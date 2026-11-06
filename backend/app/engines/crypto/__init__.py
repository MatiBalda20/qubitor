from app.engines.base import Engine, Finding
from app.engines.crypto.classic import scan_classic
from app.engines.crypto.pqc import scan_pqc

class CryptoEngine(Engine):
    name = "crypto"

    def scan(self, repo_path: str) -> list[Finding]:
        findings = []
        findings.extend(scan_classic(repo_path))
        findings.extend(scan_pqc(repo_path))
        
        # Deduplicación: Si una línea tiene RSA < 2048 como rsa-weak-key (HIGH),
        # descartamos el hallazgo pqc.rsa-keygen (MEDIUM) en la misma línea.
        weak_rsa_keys = {(f.file_path, f.line) for f in findings if f.rule_id == "crypto.classic.rsa-weak-key"}
        
        filtered = []
        for f in findings:
            if f.rule_id == "crypto.pqc.rsa-keygen" and (f.file_path, f.line) in weak_rsa_keys:
                continue
            filtered.append(f)
            
        return filtered