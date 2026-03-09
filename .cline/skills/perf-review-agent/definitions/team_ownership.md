# Team Ownership Map — Who to Contact for Each Finding

## By Problem Category

| Problem Category | Owner Team | Workflow Node |
|-----------------|------------|---------------|
| Uptime / test condition | Test Engineer (re-run test) | flow1: node_04 |
| ANR / FATAL crash | App Team of affected app | flow1: node_05 |
| Touch Duration high | System Team | flow1: node_07 |
| Running time increased | App Team | flow2: node_05 |
| Compiler type = verify | App Team (apply speed-profile) | flow2: node_15 |
| CPU frequency low | System Team (scheduler/DVFS) | flow2: node_17 |
| Binder count increased | App Team | flow2: node_24 |
| Thread priority low | System Team (scheduler) | flow2: node_34 |
| BEKS mismatch | System Team (security config) | flow2: node_38 |
| Start/Kill count mismatch | App Team + SWPL | flow2: node_39 |
| LoadApkAssets high | App Team (APK optimization) | flow3: node_01 |
| Uninterruptible Sleep / Block I/O | Multiple (see below) | flow3: node_02 |
| Memory (MemFree/MemAvailable) low | Kernel Memory Team | flow3: node_13 |
| APK size increased | App Team | flow3: node_15 |
| Pageboost decreased | Kernel Memory Team | flow3: node_21 |
| Parallel process abnormal | App Team + SWPL | flow3: node_26 |
| Top CPU process excessive | SWPL (check with process owner) | flow3: node_28 |
| PSS memory increased | App Team | flow3: node_30 |
| Exec time regression DUT1→DUT2 | App Team | flow4: node_09 |
| Bind Application regression | App Team (Application.onCreate) | flow4: node_12 |
| Compiler degraded across versions | App Team | flow4: node_14 |
| Memory regression across versions | Kernel Memory Team | flow4: node_16 |
| New crashes in DUT2 | App Team (URGENT) | flow4: node_18 |
| New kill reasons in DUT2 | App Team + SWPL | flow4: node_20 |
| PSS regression DUT1→DUT2 | App Team | flow4: node_21 |

## Block I/O — Sub-routing
When `Uninterruptible Sleep` is high, the root cause determines owner:
- High `loadApkAssets` → **App Team** (optimize APK asset loading)
- Low `MemFree` → **Kernel Memory Team** (memory pressure causing more I/O)
- Low `Pageboostd_MB` → **Kernel Memory Team** (prefetch not working)
- None of above → **System Team** (storage I/O scheduler)

## App Team Mapping (per app)
| App keyword | Package | Owner team hint |
|-------------|---------|-----------------|
| camera | com.sec.android.app.camera | Camera App TG |
| clock | com.sec.android.app.clockpackage | Clock App TG |
| gallery | com.sec.android.gallery3d | Gallery App TG |
| contact | com.samsung.android.app.contacts | Contacts App TG |
| calendar | com.samsung.android.calendar | Calendar App TG |
| calculator | com.sec.android.app.popupcalculator | Calculator App TG |
| message | com.samsung.android.messaging | Message App TG |
| setting | com.android.settings | Settings App TG |
| internet | com.sec.android.app.sbrowser | Internet App TG |
| note | com.samsung.android.app.notes | Notes App TG |
| voice | com.sec.android.app.voicenote | VoiceNote App TG |
| myfile | com.sec.android.app.myfiles | MyFiles App TG |
