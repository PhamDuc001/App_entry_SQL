#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rule Screening Script – Áp dụng 3-flow diagnostic rules tự động.

Chạy: python rule_screening.py --dut <dut.json> --ref <ref.json> [--output <output.json>]

Script này load DUT + REF JSON files, apply tất cả rule checks từ 3 flows,
và output screening_result.json chứa pass/fail cho từng app.
AI Agent sau đó chỉ cần focus phân tích sâu các app FAIL.
"""

import json
import argparse
import os
from datetime import datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THRESHOLDS (matching gauss/workflow JSON rules)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THRESHOLDS = {
    # Flow 1: Initial Validation
    "uptime_minutes": 10,           # uptime > 10 mins → invalid
    "touch_duration_diff": 10,      # DUT - REF > 10ms
    # Flow 2: Core Performance State
    "running_diff": 50,             # DUT.Running - REF.Running > 50ms
    "sleeping_diff": 50,            # DUT.Sleeping - REF.Sleeping > 50ms
    "runnable_diff": 50,            # DUT.Runnable - REF.Runnable > 50ms
    "binder_count_diff": 10,        # DUT.binder.count - REF.binder.count > 10
    "frequency_pct_diff": 15,       # high-freq % diff > 15%
    "priority_pct_diff": 15,        # high-priority % diff > 15%
    # Flow 3: Resource & Process
    "d_state_diff": 30,             # DUT.D-state - REF.D-state > 30ms
    "mem_free_diff": 50,            # REF.MemFree - DUT.MemFree > 50MB
    "mem_available_diff": 50,       # REF.MemAvailable - DUT.MemAvailable > 50MB
    "pageboost_diff": 10,           # REF.Pageboost - DUT.Pageboost > 10MB
    "pss_diff": 50,                 # DUT.PSS - REF.PSS > 50MB
    "top_cpu_diff": 300,            # process.diff > 300ms
    "loadapkassets_diff": 50,       # LoadApkAsset time diff > 50ms
}


def safe_get(data, *keys, default=None):
    """Safely navigate nested dict/list."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
        if current is None:
            return default
    return current


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLOW 1: Initial Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_uptime(dut_entry, ref_entry):
    """node_01: uptime > 10 mins → invalid test condition."""
    dut_uptime = safe_get(dut_entry, "extend", "abnormal", "uptime_minutes", default=0)
    ref_uptime = safe_get(ref_entry, "extend", "abnormal", "uptime_minutes", default=0)
    triggered = dut_uptime > THRESHOLDS["uptime_minutes"] or ref_uptime > THRESHOLDS["uptime_minutes"]
    return {
        "check": "uptime_check",
        "flow": 1,
        "triggered": triggered,
        "dut_value": dut_uptime,
        "ref_value": ref_uptime,
        "threshold": THRESHOLDS["uptime_minutes"],
        "problem": "Test condition invalid – uptime > 10 mins" if triggered else None,
        "suggestion": "Suggest re-test DUT or REF" if triggered else None,
        "team": "Test Team" if triggered else None,
    }


def check_touch_duration(dut_entry, ref_entry):
    """node_03: Touch duration diff > 10ms."""
    dut_val = safe_get(dut_entry, "sequence", "Touch Down ~ Start Proc", default=0)
    ref_val = safe_get(ref_entry, "sequence", "Touch Down ~ Start Proc", default=0)
    diff = round(dut_val - ref_val, 3)
    triggered = diff > THRESHOLDS["touch_duration_diff"]
    return {
        "check": "touch_duration_check",
        "flow": 1,
        "triggered": triggered,
        "dut_value": dut_val,
        "ref_value": ref_val,
        "diff": diff,
        "threshold": THRESHOLDS["touch_duration_diff"],
        "problem": f"Touch duration higher on DUT by {diff} ms" if triggered else None,
        "suggestion": "Suggest system team check touch input" if triggered else None,
        "team": "System Team" if triggered else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLOW 2: Core Performance State Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_state_diff(dut_entry, ref_entry, state_key, threshold_key, check_name):
    """Generic check for Running/Sleeping/Runnable state diffs."""
    dut_val = safe_get(dut_entry, "sequence", state_key, default=0)
    ref_val = safe_get(ref_entry, "sequence", state_key, default=0)
    diff = round(dut_val - ref_val, 3)
    triggered = diff > THRESHOLDS[threshold_key]
    team_map = {
        "running_check": "App Team",
        "sleeping_check": "App Team",
        "runnable_check": "System Team",
    }
    return {
        "check": check_name,
        "flow": 2,
        "triggered": triggered,
        "dut_value": round(dut_val, 3),
        "ref_value": round(ref_val, 3),
        "diff": diff,
        "threshold": THRESHOLDS[threshold_key],
        "problem": f"{state_key} increased {diff} ms" if triggered else None,
        "suggestion": f"Suggest {team_map.get(check_name, 'team')} check" if triggered else None,
        "team": team_map.get(check_name) if triggered else None,
    }


def check_compiler(dut_entry, ref_entry):
    """node_10: compiler == verify AND DUT != REF."""
    dut_compiler = safe_get(dut_entry, "extend", "abnormal", "compiler", default="unknown")
    ref_compiler = safe_get(ref_entry, "extend", "abnormal", "compiler", default="unknown")
    triggered = dut_compiler == "verify" and dut_compiler != ref_compiler
    return {
        "check": "compiler_check",
        "flow": 2,
        "sub_of": "running_check",
        "triggered": triggered,
        "dut_value": dut_compiler,
        "ref_value": ref_compiler,
        "problem": "App compiler type is verify (DUT ≠ REF)" if triggered else None,
        "suggestion": "Suggest App TG apply speed-profile" if triggered else None,
        "team": "App TG" if triggered else None,
    }


def check_binder(dut_entry, ref_entry):
    """node_19: binder count diff > 10."""
    dut_count = safe_get(dut_entry, "binder_transaction", "count", default=0)
    ref_count = safe_get(ref_entry, "binder_transaction", "count", default=0)
    diff = dut_count - ref_count
    triggered = diff > THRESHOLDS["binder_count_diff"]
    return {
        "check": "binder_check",
        "flow": 2,
        "sub_of": "sleeping_check",
        "triggered": triggered,
        "dut_value": dut_count,
        "ref_value": ref_count,
        "diff": diff,
        "threshold": THRESHOLDS["binder_count_diff"],
        "problem": f"Binder transactions increased by {diff}" if triggered else None,
        "suggestion": "Suggest App team check binder increase" if triggered else None,
        "team": "App Team" if triggered else None,
    }


def check_start_state(dut_entry, ref_entry):
    """node_04: DUT=Cold AND REF=Warm mismatch."""
    dut_states = safe_get(dut_entry, "State", default=[])
    ref_states = safe_get(ref_entry, "State", default=[])
    mismatches = []
    for i, (d, r) in enumerate(zip(dut_states, ref_states)):
        if str(d).upper() == "COLD" and str(r).upper() == "WARM":
            mismatches.append(i + 1)
    triggered = len(mismatches) > 0
    return {
        "check": "start_state_check",
        "flow": 2,
        "triggered": triggered,
        "dut_states": dut_states,
        "ref_states": ref_states,
        "mismatch_cycles": mismatches,
        "problem": f"Cold/Warm mismatch at cycle(s) {mismatches}" if triggered else None,
        "suggestion": "Suggest App team check start/kill issue" if triggered else None,
        "team": "App Team + SWPL" if triggered else None,
    }


def check_frequency(dut_entry, ref_entry):
    """node_12: Compare highest frequency percentage DUT vs REF."""
    dut_freq = safe_get(dut_entry, "frequency_by_cycle", default=[])
    ref_freq = safe_get(ref_entry, "frequency_by_cycle", default=[])
    issues = []
    sections = ["bindApplication", "activityStart", "activityResume", "Choreographer"]

    for dut_cycle, ref_cycle in zip(dut_freq, ref_freq):
        cycle_num = dut_cycle.get("cycle", "?")
        dut_data = dut_cycle.get("data", {})
        ref_data = ref_cycle.get("data", {})

        for section in sections:
            dut_sec = dut_data.get(section, [])
            ref_sec = ref_data.get(section, [])
            if not dut_sec or not ref_sec:
                continue

            # Find highest frequency and its percentage
            dut_max = max(dut_sec, key=lambda x: x.get("frequency", 0))
            ref_max = max(ref_sec, key=lambda x: x.get("frequency", 0))

            if dut_max["frequency"] == ref_max["frequency"]:
                pct_diff = ref_max["percentage"] - dut_max["percentage"]
                if pct_diff > THRESHOLDS["frequency_pct_diff"]:
                    issues.append({
                        "cycle": cycle_num,
                        "section": section,
                        "frequency": dut_max["frequency"],
                        "dut_pct": dut_max["percentage"],
                        "ref_pct": ref_max["percentage"],
                        "diff_pct": round(pct_diff, 2),
                    })

    triggered = len(issues) > 0
    return {
        "check": "frequency_check",
        "flow": 2,
        "sub_of": "running_check",
        "triggered": triggered,
        "issues": issues,
        "threshold": THRESHOLDS["frequency_pct_diff"],
        "problem": "App running at lower CPU frequency" if triggered else None,
        "suggestion": "Suggest system team check frequency" if triggered else None,
        "team": "System Team" if triggered else None,
    }


def check_priority(dut_entry, ref_entry):
    """node_08: Compare highest priority percentage DUT vs REF."""
    dut_prio = safe_get(dut_entry, "priority_by_cycle", default=[])
    ref_prio = safe_get(ref_entry, "priority_by_cycle", default=[])
    issues = []
    sections = ["bindApplication", "activityStart", "activityResume", "Choreographer"]

    for dut_cycle, ref_cycle in zip(dut_prio, ref_prio):
        cycle_num = dut_cycle.get("cycle", "?")
        dut_data = dut_cycle.get("data", {})
        ref_data = ref_cycle.get("data", {})

        for section in sections:
            dut_sec = dut_data.get(section, [])
            ref_sec = ref_data.get(section, [])
            if not dut_sec or not ref_sec:
                continue

            # Highest priority = lowest number
            dut_best = min(dut_sec, key=lambda x: x.get("priority", 999))
            ref_best = min(ref_sec, key=lambda x: x.get("priority", 999))

            if dut_best["priority"] == ref_best["priority"]:
                pct_diff = ref_best["percentage"] - dut_best["percentage"]
                if pct_diff > THRESHOLDS["priority_pct_diff"]:
                    issues.append({
                        "cycle": cycle_num,
                        "section": section,
                        "priority": dut_best["priority"],
                        "dut_pct": dut_best["percentage"],
                        "ref_pct": ref_best["percentage"],
                        "diff_pct": round(pct_diff, 2),
                    })

    triggered = len(issues) > 0
    return {
        "check": "priority_check",
        "flow": 2,
        "sub_of": "runnable_check",
        "triggered": triggered,
        "issues": issues,
        "threshold": THRESHOLDS["priority_pct_diff"],
        "problem": "Lower thread priority on DUT" if triggered else None,
        "suggestion": "Suggest system team check scheduling" if triggered else None,
        "team": "System Team" if triggered else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLOW 3: Resource Usage & Process Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_d_state(dut_entry, ref_entry):
    """node_02: Uninterruptible Sleep (D-state) diff > 30ms."""
    dut_val = safe_get(dut_entry, "sequence", "Uninterruptible Sleep", default=0)
    ref_val = safe_get(ref_entry, "sequence", "Uninterruptible Sleep", default=0)
    diff = round(dut_val - ref_val, 3)
    triggered = diff > THRESHOLDS["d_state_diff"]
    return {
        "check": "d_state_check",
        "flow": 3,
        "triggered": triggered,
        "dut_value": round(dut_val, 3),
        "ref_value": round(ref_val, 3),
        "diff": diff,
        "threshold": THRESHOLDS["d_state_diff"],
        "problem": f"D-state (Block I/O) increased {diff} ms" if triggered else None,
        "suggestion": "Suggest Kernel Memory team check" if triggered else None,
        "team": "Kernel Memory Team" if triggered else None,
    }


def check_memory(dut_entry, ref_entry):
    """node_07: Memory free/available decreased > 50MB."""
    dut_mem_free = safe_get(dut_entry, "extend", "memory", "MemFree_MB", default=None)
    ref_mem_free = safe_get(ref_entry, "extend", "memory", "MemFree_MB", default=None)
    dut_mem_avail = safe_get(dut_entry, "extend", "memory", "MemAvailable_MB", default=None)
    ref_mem_avail = safe_get(ref_entry, "extend", "memory", "MemAvailable_MB", default=None)

    issues = []
    if dut_mem_free is not None and ref_mem_free is not None:
        diff = round(ref_mem_free - dut_mem_free, 2)
        if diff > THRESHOLDS["mem_free_diff"]:
            issues.append({"metric": "MemFree_MB", "dut": dut_mem_free, "ref": ref_mem_free, "diff": diff})
    if dut_mem_avail is not None and ref_mem_avail is not None:
        diff = round(ref_mem_avail - dut_mem_avail, 2)
        if diff > THRESHOLDS["mem_available_diff"]:
            issues.append({"metric": "MemAvailable_MB", "dut": dut_mem_avail, "ref": ref_mem_avail, "diff": diff})

    triggered = len(issues) > 0
    return {
        "check": "memory_check",
        "flow": 3,
        "sub_of": "d_state_check",
        "triggered": triggered,
        "issues": issues,
        "threshold": THRESHOLDS["mem_free_diff"],
        "problem": "Memory free/available decreased" if triggered else None,
        "suggestion": "Suggest Kernel Memory team check" if triggered else None,
        "team": "Kernel Memory Team" if triggered else None,
    }


def check_pageboost(dut_entry, ref_entry):
    """node_11: Pageboost prefetch decreased > 10MB."""
    dut_val = safe_get(dut_entry, "extend", "memory", "Pageboostd_MB", default=None)
    ref_val = safe_get(ref_entry, "extend", "memory", "Pageboostd_MB", default=None)
    if dut_val is None or ref_val is None:
        return {"check": "pageboost_check", "flow": 3, "triggered": False, "problem": None, "data_available": False}
    diff = round(ref_val - dut_val, 2)
    triggered = diff > THRESHOLDS["pageboost_diff"]
    return {
        "check": "pageboost_check",
        "flow": 3,
        "sub_of": "d_state_check",
        "triggered": triggered,
        "dut_value": dut_val,
        "ref_value": ref_val,
        "diff": diff,
        "threshold": THRESHOLDS["pageboost_diff"],
        "problem": f"Pageboost prefetch decreased {diff} MB" if triggered else None,
        "suggestion": "Suggest Kernel Memory team check pageboost" if triggered else None,
        "team": "Kernel Memory Team" if triggered else None,
    }


def check_pss(dut_entry, ref_entry):
    """node_25: PSS diff > 50MB."""
    dut_val = safe_get(dut_entry, "extend", "memory", "App_PSS_MB", default=None)
    ref_val = safe_get(ref_entry, "extend", "memory", "App_PSS_MB", default=None)
    if dut_val is None or ref_val is None:
        return {"check": "pss_check", "flow": 3, "triggered": False, "problem": None, "data_available": False}
    diff = round(dut_val - ref_val, 2)
    triggered = diff > THRESHOLDS["pss_diff"]
    return {
        "check": "pss_check",
        "flow": 3,
        "triggered": triggered,
        "dut_value": dut_val,
        "ref_value": ref_val,
        "diff": diff,
        "threshold": THRESHOLDS["pss_diff"],
        "problem": f"PSS memory increased {diff} MB" if triggered else None,
        "suggestion": "Suggest app owner debug PSS increase" if triggered else None,
        "team": "App Owner" if triggered else None,
    }


def check_parallel_process(dut_entry):
    """node_23: start_process_abnormal has any process."""
    abnormal = safe_get(dut_entry, "extend", "start_process_abnormal", default=[])
    all_processes = []
    for cycle_idx, cycle in enumerate(abnormal):
        if isinstance(cycle, list) and len(cycle) > 0:
            for proc in cycle:
                all_processes.append({"cycle": cycle_idx + 1, "process": proc})
    triggered = len(all_processes) > 0
    return {
        "check": "parallel_process_check",
        "flow": 3,
        "triggered": triggered,
        "processes": all_processes,
        "problem": f"Parallel process detected: {[p['process'] for p in all_processes]}" if triggered else None,
        "suggestion": "Suggest App team and SWPL investigate" if triggered else None,
        "team": "App Team + SWPL" if triggered else None,
    }


def check_top_cpu(dut_entry):
    """node_24: top process CPU diff > 300ms."""
    top_cpu = safe_get(dut_entry, "top_process_consume_by_cycle", default=[])
    issues = []
    for cycle_data in top_cpu:
        cycle_num = cycle_data.get("cycle", "?")
        for proc in cycle_data.get("process", []):
            diff = proc.get("diff", 0)
            if diff > THRESHOLDS["top_cpu_diff"]:
                issues.append({
                    "cycle": cycle_num,
                    "process": proc["name"],
                    "dut": proc.get("dut", 0),
                    "ref": proc.get("ref", 0),
                    "diff": diff,
                })
    triggered = len(issues) > 0
    return {
        "check": "top_cpu_check",
        "flow": 3,
        "triggered": triggered,
        "issues": issues,
        "threshold": THRESHOLDS["top_cpu_diff"],
        "problem": f"Top CPU consumers: {[(i['process'], i['diff']) for i in issues]}" if triggered else None,
        "suggestion": "Suggest SWPL check with process owner" if triggered else None,
        "team": "SWPL" if triggered else None,
    }


def check_loadapkassets(dut_entry, ref_entry):
    """Check LoadApkAsset time and processes."""
    dut_assets = safe_get(dut_entry, "extend", "loadapkassets", default={})
    ref_assets = safe_get(ref_entry, "extend", "loadapkassets", default={})
    
    dut_total = round(sum(dut_assets.values()), 3) if dut_assets else 0
    ref_total = round(sum(ref_assets.values()), 3) if ref_assets else 0
    dut_count = len(dut_assets) if dut_assets else 0
    ref_count = len(ref_assets) if ref_assets else 0
    
    issues = []
    
    # Check 1: DUT có loadapkassets nhưng REF không có
    if dut_total > THRESHOLDS["loadapkassets_diff"] and ref_total == 0:
        issues.append({
            "type": "dut_only",
            "dut_total": dut_total,
            "ref_total": ref_total,
            "dut_count": dut_count,
            "ref_count": ref_count,
            "processes": list(dut_assets.keys()),
            "details": dut_assets
        })
    
    # Check 2: Cả 2 có, so sánh diff > 50ms
    elif dut_total > 0 and ref_total > 0:
        diff = round(dut_total - ref_total, 3)
        if diff > THRESHOLDS["loadapkassets_diff"]:
            issues.append({
                "type": "increased",
                "dut_total": dut_total,
                "ref_total": ref_total,
                "diff": diff,
                "dut_count": dut_count,
                "ref_count": ref_count
            })
    
    # Check 3: DUT có nhiều processes hơn REF
    if dut_total > 0 and ref_total > 0 and dut_count > ref_count:
        issues.append({
            "type": "more_processes",
            "dut_count": dut_count,
            "ref_count": ref_count,
            "dut_total": dut_total,
            "ref_total": ref_total
        })
    
    triggered = len(issues) > 0
    problem_desc = None
    if triggered:
        if issues[0]["type"] == "dut_only":
            problem_desc = f"LoadApkAsset detected on DUT ({dut_total} ms, {dut_count} processes) but not on REF"
        elif issues[0]["type"] == "increased":
            problem_desc = f"LoadApkAsset increased by {issues[0]['diff']} ms (DUT: {dut_total} ms, REF: {ref_total} ms)"
        elif issues[0]["type"] == "more_processes":
            problem_desc = f"LoadApkAsset: DUT has more processes ({dut_count}) than REF ({ref_count})"
    
    return {
        "check": "loadapkassets_check",
        "flow": 3,
        "triggered": triggered,
        "issues": issues,
        "dut_value": dut_assets,
        "ref_value": ref_assets,
        "dut_total": dut_total,
        "ref_total": ref_total,
        "threshold": THRESHOLDS["loadapkassets_diff"],
        "problem": problem_desc,
        "suggestion": "Suggest System Team check APK cache/Pageboost prefetch mechanism" if triggered else None,
        "team": "System Team" if triggered else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN: Screen all apps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def screen_app(dut_app_data, ref_app_data):
    """Run all 3 flows for one app. Returns list of check results."""
    dut_entry = dut_app_data.get("entry", {})
    ref_entry = ref_app_data.get("entry", {}) if ref_app_data else {}

    checks = []

    # Flow 1: Initial Validation
    checks.append(check_uptime(dut_entry, ref_entry))
    checks.append(check_touch_duration(dut_entry, ref_entry))

    # Flow 2: Core Performance State
    checks.append(check_state_diff(dut_entry, ref_entry, "Running", "running_diff", "running_check"))
    checks.append(check_compiler(dut_entry, ref_entry))
    checks.append(check_frequency(dut_entry, ref_entry))
    checks.append(check_state_diff(dut_entry, ref_entry, "Sleeping", "sleeping_diff", "sleeping_check"))
    checks.append(check_binder(dut_entry, ref_entry))
    checks.append(check_state_diff(dut_entry, ref_entry, "Runnable", "runnable_diff", "runnable_check"))
    checks.append(check_priority(dut_entry, ref_entry))
    checks.append(check_start_state(dut_entry, ref_entry))

    # Flow 3: Resource & Process
    checks.append(check_d_state(dut_entry, ref_entry))
    checks.append(check_memory(dut_entry, ref_entry))
    checks.append(check_pageboost(dut_entry, ref_entry))
    checks.append(check_pss(dut_entry, ref_entry))
    checks.append(check_loadapkassets(dut_entry, ref_entry))
    checks.append(check_parallel_process(dut_entry))
    checks.append(check_top_cpu(dut_entry))

    return checks


def determine_status(checks):
    """Determine overall app status from check results."""
    triggered = [c for c in checks if c.get("triggered")]
    if not triggered:
        return "PASS"
    # Check for critical issues (Flow 1 failures)
    flow1_fails = [c for c in triggered if c.get("flow") == 1]
    if flow1_fails:
        return "INVALID"
    return "FAIL"


def main():
    parser = argparse.ArgumentParser(description="Rule Screening – 3-flow diagnostic")
    parser.add_argument("--dut", required=True, help="Path to DUT JSON file")
    parser.add_argument("--ref", required=True, help="Path to REF JSON file")
    parser.add_argument("--output", default=None, help="Output path (default: same dir as DUT)")
    args = parser.parse_args()

    # Load JSON files
    with open(args.dut, "r", encoding="utf-8") as f:
        dut_data = json.load(f)
    with open(args.ref, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    # Build REF lookup by app name
    ref_apps = {}
    for app_data in ref_data.get("apps_data", []):
        ref_apps[app_data["app"]] = app_data

    # Screen each DUT app
    results = []
    summary = {"total": 0, "pass": 0, "fail": 0, "invalid": 0}

    for dut_app_data in dut_data.get("apps_data", []):
        app_name = dut_app_data["app"]
        ref_app_data = ref_apps.get(app_name)

        checks = screen_app(dut_app_data, ref_app_data)
        status = determine_status(checks)
        triggered_checks = [c for c in checks if c.get("triggered")]
        teams_involved = list(set(c["team"] for c in triggered_checks if c.get("team")))

        app_result = {
            "app": app_name,
            "status": status,
            "triggered_count": len(triggered_checks),
            "total_checks": len(checks),
            "teams": teams_involved,
            "triggered_checks": triggered_checks,
            "all_checks": checks,
        }
        results.append(app_result)

        summary["total"] += 1
        summary[status.lower()] += 1

    # Build output
    output = {
        "screening_timestamp": datetime.now().isoformat(),
        "dut_file": os.path.basename(args.dut),
        "ref_file": os.path.basename(args.ref),
        "dut_info": {
            "device_code": dut_data.get("device_code"),
            "version": dut_data.get("version"),
        },
        "ref_info": {
            "device_code": ref_data.get("device_code"),
            "version": ref_data.get("version"),
        },
        "thresholds": THRESHOLDS,
        "summary": summary,
        "apps": results,
    }

    # Save output
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.dirname(args.dut)
        output_path = os.path.join(output_dir, "screening_result.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Rule Screening Complete")
    print(f"{'='*60}")
    print(f"  DUT: {dut_data.get('device_code')} / {dut_data.get('version')}")
    print(f"  REF: {ref_data.get('device_code')} / {ref_data.get('version')}")
    print(f"  Total apps: {summary['total']}")
    print(f"   PASS:    {summary['pass']}")
    print(f"   FAIL:    {summary['fail']}")
    print(f"   INVALID: {summary['invalid']}")
    print(f"{'='*60}")

    for app in results:
        icon = {"PASS": "OK", "FAIL": "Fail", "INVALID": "Warning"}.get(app["status"], "?")
        print(f"  {icon} {app['app']}: {app['status']} ({app['triggered_count']}/{app['total_checks']} checks triggered)")
        for check in app.get("triggered_checks", []):
            print(f"      → [{check['check']}] {check.get('problem', '')}")
            print(f"        Team: {check.get('team', 'N/A')}")

    print(f"\n  Output saved: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
