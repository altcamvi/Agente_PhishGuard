"""Pruebas del pipeline de datos del Hito 2 con corpus SINTETICOS (no hay correos reales en el repositorio).
Ejecutar:  python -m unittest discover -s tests -v
"""
import functools, gzip, http.server, io, json, pathlib, random, sys, tarfile, tempfile, threading, unittest
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))
from phishguard import dataprep as dp   # noqa: E402
import anonymize, make_splits, baseline, download_data, make_hito2_report   # noqa: E402

SALT = b"sal-de-prueba"
RAW_ENRON = (b"Message-ID: <123.JavaMail.evans@thyme>\nDate: Mon, 14 May 2001 16:39:00 -0700 (PDT)\n"
             b"From: \"John Smith\" <john.smith@enron.com>\nTo: mary.jones@enron.com\nSubject: Reunion Enron\n"
             b"X-Folder: \\Smith\\Inbox\nReceived: from mail.enron.com by x\n\n"
             b"Hola, llama al 555-123-4567 o a +57 300 123 4567. Escribe a john.smith@enron.com.\n"
             b"Mira http://intranet.example.com/doc?id=7 .\n")


def fake_phish(i, rnd):
    return (f"From: Banco {rnd.randint(1,99)} <seguridad{i}@banc0-secure{rnd.randint(1,9)}.ru>\nSubject: Verify your account now {i}\n\n"
            f"Urgent: your account {rnd.randint(1000,9999)} is suspended. Click http://secure-login{i}.example.ru/v?u={i} "
            f"to verify your password immediately or lose access. Dear customer, reference {rnd.random()}\n").encode()


def fake_ham(i, rnd, word="projet"):
    return (f"From: Colega {i} <colega{i}@empresa.com>\nSubject: Reunion {word} {i}\n\n"
            f"Hi team, the meeting about {word} number {rnd.randint(1,500)} moved to {rnd.randint(1,12)}pm. "
            f"Please review the draft and send comments, thanks. note {rnd.random()}\n").encode()


def add_tar(path, members, mode):
    with tarfile.open(path, mode) as tf:
        for name, data in members:
            ti = tarfile.TarInfo(name); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))


def make_raw(root: pathlib.Path):
    rnd = random.Random(1)
    (root / "spamassassin").mkdir(parents=True); (root / "enron").mkdir(); (root / "nazario").mkdir(); (root / "nigerian").mkdir()
    add_tar(root / "spamassassin" / "20030228_easy_ham.tar.bz2",
            [(f"easy_ham/{i:04d}.x", b"From a@b.com Thu Aug 22 2002\n" + fake_ham(i, rnd, "spamassassin")) for i in range(250)] +
            [("easy_ham/cmds", b"ignorar")], "w:bz2")
    add_tar(root / "spamassassin" / "20030228_spam.tar.bz2", [("spam/0001.x", fake_phish(9999, rnd))], "w:bz2")
    add_tar(root / "enron" / "enron_mail_20150507.tar.gz",
            [(f"maildir/user{i%7}/inbox/{i}.", fake_ham(i + 1000, rnd, "enron")) for i in range(300)], "w:gz")
    mbox = b"".join(b"From phish@x.ru Mon Jan  1 00:00:00 2024\n" + fake_phish(i, rnd) + b"\n" for i in range(220))
    (root / "nazario" / "phishing-2024.mbox").write_bytes(mbox)
    (root / "nazario" / "private-phishing4.mbox").write_bytes(b"From x Mon\n" + fake_phish(77777, rnd))
    for i in range(150):
        (root / "nigerian" / f"{i}.eml").write_bytes(
            (f"From: Prince {i} <p{i}@mail.ng>\nSubject: Business proposal {i}\n\nDear friend, I have {rnd.randint(1,50)} million "
             f"dollars to transfer, send your bank account urgently {rnd.random()}\n").encode())


class TestAnonymize(unittest.TestCase):
    def setUp(self):
        self.a = dp.Anonymizer(SALT)
        self.rec = dp.sanitize_message(RAW_ENRON, self.a)

    def test_removes_identifiers_and_revealing_headers(self):
        raw = self.rec["raw"].lower()
        for bad in ("john.smith", "john smith", "mary.jones", "message-id", "date:", "received", "x-folder",
                    "555-123", "300 123", "enron", "javamail"):
            self.assertNotIn(bad, raw, bad)
        self.assertNotIn("acme", raw)                      # no debe haber un token unico de sustitucion (seria un atajo)
        self.assertIn("[tel]", raw)
        self.assertIn("http://intranet.example.com/doc?id=7", self.rec["raw"])   # las URLs se conservan

    def test_hash_is_deterministic_and_salt_dependent(self):
        b = dp.sanitize_message(RAW_ENRON, dp.Anonymizer(SALT))
        c = dp.sanitize_message(RAW_ENRON, dp.Anonymizer(b"otra-sal"))
        self.assertEqual(self.rec["raw"], b["raw"])
        self.assertNotEqual(self.rec["raw"], c["raw"])

    def test_attachment_keeps_all_extensions(self):
        raw = (b"From: a@b.com\nSubject: x\nMIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=B\n\n--B\n"
               b"Content-Type: text/plain\n\nhola\n--B\nContent-Type: application/octet-stream\n"
               b"Content-Disposition: attachment; filename=\"Factura.pdf.exe\"\n\nAAAA\n--B--\n")
        r = dp.sanitize_message(raw, dp.Anonymizer(SALT))
        self.assertEqual(r["n_attachments"], 1)
        self.assertIn(".pdf.exe", r["raw"]); self.assertNotIn("Factura", r["raw"])

    def test_empty_message_is_dropped(self):
        self.assertIsNone(dp.sanitize_message(b"X-Foo: 1\n\n", self.a))


class TestReading(unittest.TestCase):
    def test_split_mbox_and_single_file_with_envelope(self):
        mb = b"From a@x Mon\nSubject: 1\n\nuno\n\nFrom b@x Tue\nSubject: 2\n\ndos\nFrom no es separador\n"
        parts = dp.split_mbox(mb)
        self.assertEqual(len(parts), 2); self.assertIn(b"From no es separador", parts[1])
        self.assertEqual(len(dp.split_mbox(b"From a@x Mon\nSubject: 1\n\ncuerpo\n")), 1)

    def test_reservoir_reads_only_selected_and_is_deterministic(self):
        reads = []
        def items():
            for i in range(200):
                yield f"n{i}", (lambda i=i: (reads.append(i), str(i).encode())[1])
        s1 = dp.reservoir_sample(items(), 20, seed=42); n_reads = len(reads)
        s2 = dp.reservoir_sample(items(), 20, seed=42)
        self.assertEqual(s1, s2); self.assertEqual(len(s1), 20); self.assertLess(n_reads, 200)

    def test_lang(self):
        self.assertEqual(dp.lang_guess("Estimado cliente, su cuenta del banco fue suspendida por seguridad y no puede acceder"), "es")
        self.assertEqual(dp.lang_guess("Dear customer, your account was suspended and you will not be able to use it"), "en")
        self.assertEqual(dp.lang_guess("12345"), "desconocido")


def frame(n_ph_a=200, n_ph_b=150, n_ha=250, n_hb=300):
    rows, k = [], 0
    for src, label, n in (("nazario", 1, n_ph_a), ("nigerian", 1, n_ph_b), ("spamassassin", 0, n_ha), ("enron", 0, n_hb)):
        for i in range(n):
            k += 1
            rows.append({"id": f"{src}-{i}", "source": src, "label": label, "text": f"{src} texto {i} " + ("phish urgent verify" if label else "meeting project"),
                         "n_attachments": 0, "lang": "en"})
    return pd.DataFrame(rows)


class TestSplitsAndDedup(unittest.TestCase):
    def test_dedup_and_conflicts(self):
        df = pd.DataFrame({"id": list("abcde"), "source": ["s"] * 5, "label": [0, 0, 1, 0, 1],
                           "text": ["hola  Mundo", "HOLA mundo", "igual", "igual", "unico"], "n_attachments": 0, "lang": "es"})
        clean, rep = dp.drop_duplicates(df)
        self.assertEqual(sorted(clean["id"]), ["a", "e"])            # 'b' duplica a 'a'; 'c' y 'd' se contradicen
        self.assertEqual(int(rep["duplicados_exactos"].sum()), 1); self.assertEqual(int(rep["etiqueta_contradictoria"].sum()), 2)

    def test_split_proportions_disjoint_stratified_deterministic(self):
        df = frame(); s = dp.stratified_split(df); s2 = dp.stratified_split(df)
        self.assertTrue((s == s2).all())
        frac = s.value_counts(normalize=True)
        self.assertAlmostEqual(frac["train"], 0.70, delta=0.02); self.assertAlmostEqual(frac["val"], 0.15, delta=0.02)
        ct = pd.crosstab([df["source"], df["label"]], s)
        self.assertTrue((ct > 0).all().all())                          # cada fuente aparece en las tres particiones
        self.assertEqual(len(s), len(df)); self.assertFalse((s == "").any())

    def test_near_duplicates_same_template_different_url_and_numbers(self):
        base = "estimado cliente su cuenta ha sido suspendida por seguridad verifique ahora mismo para evitar el cierre definitivo " * 3
        df = pd.DataFrame({"id": list("abcd"), "source": ["s"] * 4, "label": [1, 1, 1, 0],
                           "text": [base + "http://a.ru/1 ref 123", base + "http://b.ru/2 ref 999", "otro texto distinto " * 20,
                                    "x " * 10], "n_attachments": 0, "lang": "es"})
        rep = dp.near_duplicate_report(df)
        self.assertEqual(int(rep[rep["label"] == 1]["en_plantilla_repetida"].iloc[0]), 2)
        clean, n = dp.drop_near_duplicates(df)
        self.assertEqual(n, 1); self.assertEqual(sorted(clean["id"]), ["a", "c", "d"])   # el corto nunca colisiona

    def test_near_dedup_conflicting_labels_dropped(self):
        base = "mensaje con la misma plantilla pero etiquetas contradictorias entre fuentes distintas " * 4
        df = pd.DataFrame({"id": ["a", "b"], "source": ["s", "t"], "label": [0, 1], "text": [base + "1", base + "2"],
                           "n_attachments": 0, "lang": "es"})
        self.assertTrue(dp.drop_near_duplicates(df)[0].empty)

    def test_too_small_raises(self):
        with self.assertRaises(ValueError): dp.stratified_split(frame(2, 2, 2, 2))

    def test_loso_plan_flags_uncalculable(self):
        plan = dp.loso_plan(frame()); self.assertTrue(plan["calculable"].all())
        plan1 = dp.loso_plan(frame(n_ph_b=0)); row = plan1[plan1["fuente_excluida"] == "nazario"].iloc[0]
        self.assertFalse(row["calculable"])


class TestEndToEnd(unittest.TestCase):
    def test_pipeline(self):
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t); make_raw(t / "raw")
            rep = anonymize.build(t / "raw", t / "proc", t / "rep")
            self.assertEqual(rep["spamassassin"]["conservados"], 250)     # sin 'cmds' ni spam
            self.assertEqual(rep["nazario"]["conservados"], 220)          # sin private-*
            self.assertEqual(rep["enron"]["conservados"], 300)
            df = make_splits.run(t / "proc", t / "rep")
            self.assertFalse(df.empty); self.assertEqual(set(df["split"]), {"train", "val", "test"})
            blob = gzip.open(t / "proc" / "emails.jsonl.gz", "rt").read().lower()
            for bad in ("colega1@", "seguridad1@", "p1@mail.ng", "message-id", "javamail"):
                self.assertNotIn(bad, blob, bad)
            for f in ("splits.csv", "dedup_report.csv", "loso_plan.csv", "shortcut_tokens.csv", "resumen_particion.csv"):
                self.assertTrue((t / "rep" / f).exists(), f)
            val = baseline.run_split(df, "val")
            b1 = val[val["modelo"] == "B1_tfidf_logreg"].iloc[0]
            self.assertGreater(b1["recall"], 0.9); self.assertLessEqual(b1["fpr"], 0.05)
            self.assertEqual(val[val["modelo"] == "B0_mayoritario"].iloc[0]["auc"], 0.5)
            loso = baseline.run_loso(df); self.assertEqual(len(loso), 4); self.assertFalse(loso["valor"].isna().any())
            # informe: con resultados y sin ellos
            val.to_csv(t / "rep" / "baseline_validacion.csv", index=False); loso.to_csv(t / "rep" / "baseline_loso.csv", index=False)
            rep_md = make_hito2_report.build(t / "rep")
            for needle in ("## 5. Líneas base", "M1 recall", "Prueba dejando una fuente fuera", "COMPLETAR POR EL EQUIPO", "nigerian"):
                self.assertIn(needle, rep_md, needle)
            self.assertIn("Tras anonimizar y deduplicar hay **920**", rep_md)
            self.assertIn("Aún no hay `download_manifest.json`", rep_md)       # no se ejecuto download_data.py en la prueba
            self.assertIn("no se ha usado todavía", rep_md)                    # el test no se toca sin --final
            empty = make_hito2_report.build(t / "nada")                  # sin ejecutar el pipeline: avisa, no falla
            self.assertIn("Aún no hay", empty); self.assertNotIn("Traceback", empty)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


class TestDownload(unittest.TestCase):
    def test_list_gate_download_and_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t); served = t / "web"; served.mkdir()
            for n in ("20030228_easy_ham.tar.bz2", "20030228_spam.tar.bz2", "20030228_hard_ham.tar.bz2"):
                (served / n).write_bytes(n.encode() * 10)
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(served)))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_address[1]}/"
            try:
                names = download_data.list_index(url, download_data.SOURCES["spamassassin"]["pattern"])
                self.assertEqual(names, ["20030228_easy_ham.tar.bz2", "20030228_hard_ham.tar.bz2"])   # el spam no se baja
                download_data.RAW, download_data.MANIFEST = t / "raw", t / "m.json"
                self.assertEqual(download_data.main(["--source", "spamassassin", "--index-url", url]), 2)   # sin confirmar terminos
                self.assertFalse((t / "raw").exists())
                self.assertEqual(download_data.main(["--source", "spamassassin", "--index-url", url, "--accept-terms", "spamassassin"]), 0)
                m = json.loads((t / "m.json").read_text())["spamassassin"]
                self.assertTrue(m["terms_accepted"]); self.assertEqual(len(m["files"]), 2)
                import hashlib
                f = m["files"][0]; self.assertEqual(f["sha256"], hashlib.sha256((t / "raw" / "spamassassin" / f["file"]).read_bytes()).hexdigest())
                with self.assertRaises(RuntimeError): download_data.download_source("enron", url, t / "raw")   # indice sin el archivo esperado
            finally:
                srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
