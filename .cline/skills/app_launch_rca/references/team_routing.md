# Team Routing – Issue → Responsible Team

## Routing Table

| Issue Category | Condition | Responsible Team | Action |
|----------------|-----------|-----------------|--------|
| **Compiler verify** | compiler == "verify" | **App TG** | Apply speed-profile compilation |
| **Running time increase** | DUT.Running - REF.Running > 50ms | **App Team** | Check app-side computation increase |
| **CPU Frequency low** | DUT high-freq% < REF by >15% | **System Team** | Check frequency governor/boosting |
| **Thread Priority low** | DUT high-priority% < REF by >15% | **System Team** | Check scheduling priority settings |
| **Binder increase** | DUT.binder.count - REF.count > 10 | **App Team** | Reduce binder calls to system services |
| **Cold/Warm mismatch** | DUT=Cold, REF=Warm | **App Team + SWPL** | Check BEKS config and start/kill reasons |
| **BEKS mismatch** | DUT BEKS ≠ REF BEKS | **System Team** | Check BEKS protection configuration |
| **Start/Kill diff** | start_reason count differs | **App Team** | Check app lifecycle management |
| **Memory decrease** | REF.MemFree - DUT.MemFree > 50MB | **Kernel Memory Team** | Investigate memory consumption |
| **Pageboost decrease** | REF.Pageboost - DUT.Pageboost > 10MB | **Kernel Memory Team** | Check pageboost operation |
| **Block I/O increase** | DUT.D-state - REF.D-state > 30ms | **Kernel Memory Team** | Check I/O scheduling, memory pressure |
| **APK size increase** | APK size diff detected | **App Team** | Optimize APK size |
| **Parallel process** | start_process_abnormal has entries | **App Team + SWPL** | Investigate parallel process launches |
| **Top CPU consumer** | process.diff > 300ms | **SWPL** | Contact process owner |
| **PSS increase** | DUT.PSS - REF.PSS > 50MB | **App Owner** | Debug memory usage increase |
| **ANR/FATAL detected** | ANR or FATAL exists | **App Team** | Fix crash/ANR issue first |
| **Touch duration high** | DUT - REF > 10ms | **System Team** | Check touch input handling |
| **Uptime invalid** | uptime > 10 mins | **Test Team** | Re-test with fresh boot |

## Team Descriptions

| Team | Scope | Examples |
|------|-------|---------|
| **App Team** | App-specific code và behavior | Samsung Camera, Gallery, Messages |
| **App TG** | App Technical Group – compilation, build | AOT profile, speed-profile |
| **System Team** | Android framework, scheduler, governor | CPU frequency, thread priority, touch |
| **Kernel Memory Team** | Kernel memory management | MemFree, pageboost, block I/O |
| **SWPL** | Software Platform team | Process management, cross-cutting concerns |
| **App Owner** | Specific app developer/maintainer | PSS optimization |
| **Test Team** | QA/Test execution | Re-test conditions |

## Escalation Priority

1. 🔴 **ANR/FATAL** → Fix first, other findings may be side effects
2. 🔴 **Uptime invalid** → Re-test required, current data may be unreliable
3. 🟡 **Running/Sleeping/Runnable > threshold** → Main performance issue
4. 🟡 **Memory/Pageboost decrease** → Resource issue
5. 🟢 **Compiler verify** → Known optimization opportunity
6. 🟢 **Touch duration** → Usually minor unless very large diff
