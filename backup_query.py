    # ---------------------------------------------------------
    # === SLEEP BREAKDOWN BY WAKER (NEW) ===
    # ---------------------------------------------------------
    row_idx += 3
    
    # Formats
    fmt_sleep_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFE4C4", "border": 1, "border_color": "#000000"}) # Bisque color
    fmt_sleep_proc = wb.add_format({"bold": True, "align": "left", "bg_color": "#F5F5F5", "border": 1})
    fmt_sleep_thread = wb.add_format({"italic": True, "align": "left", "indent": 1, "border": 1})
    fmt_sleep_tag = wb.add_format({"align": "left", "indent": 2, "border": 1, "font_color": "#333333"})
    fmt_sleep_val = wb.add_format({"num_format": "0.0", "align": "center", "border": 1})

    # [FIXED HERE] Thêm 'if cycle else None' để tránh crash khi cycle bị None
    all_dut_sleep = [cycle.get("Sleep_Waker_Data", None) if cycle else None for cycle in dut_cycles]
    all_ref_sleep = [cycle.get("Sleep_Waker_Data", None) if cycle else None for cycle in ref_cycles]
    
    # Check data
    has_sleep_data = False
    for df in all_dut_sleep + all_ref_sleep:
        if df is not None and not df.empty:
            has_sleep_data = True; break
            
    if has_sleep_data:
        # 1. Header
        ws.merge_range(row_idx, 0, row_idx, 0, "Sleep Woken-By Analysis", fmt_sleep_header)
        col_idx = 1
        for i in range(len(dut_cycles)):
            ws.write(row_idx, col_idx, f"DUT Cy{i+1}", fmt_sleep_header)
            col_idx += 1
        for i in range(len(ref_cycles)):
            ws.write(row_idx, col_idx, f"REF Cy{i+1}", fmt_sleep_header)
            col_idx += 1
        row_idx += 1
        
        ws.write(row_idx, 0, "Waker Process > Thread > Tag", fmt_sleep_header)
        for col in range(1, col_idx): ws.write(row_idx, col, "Dur (ms)", fmt_sleep_header)
        row_idx += 1

        # 2. Aggregate Keys (Process -> Thread -> Tag)
        tree_keys = defaultdict(lambda: defaultdict(set))
        
        for df_list in [all_dut_sleep, all_ref_sleep]:
            for df in df_list:
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        proc = str(row['waker_process'])
                        th = str(row['waker_thread'])
                        tag = str(row['waker_tag'])
                        tree_keys[proc][th].add(tag)
        
        sorted_procs = sorted(tree_keys.keys())
        
        # 3. Draw Table
        for proc in sorted_procs:
            # Draw Process Row
            ws.write(row_idx, 0, proc, fmt_sleep_proc)
            for col in range(1, col_idx): ws.write(row_idx, col, "", fmt_sleep_proc)
            row_idx += 1
            
            sorted_threads = sorted(tree_keys[proc].keys())
            for th in sorted_threads:
                # Draw Thread Row
                ws.write(row_idx, 0, f"Thread: {th}", fmt_sleep_thread)
                for col in range(1, col_idx): ws.write(row_idx, col, "", fmt_sleep_thread)
                row_idx += 1
                
                sorted_tags = sorted(list(tree_keys[proc][th]))
                for tag in sorted_tags:
                    # Draw Tag Row (Data Row)
                    ws.write(row_idx, 0, f"Tag: {tag}", fmt_sleep_tag)
                    current_col = 1
                    
                    # Fill DUT
                    for df in all_dut_sleep:
                        val = ""
                        if df is not None:
                            match = df[
                                (df['waker_process'] == proc) & 
                                (df['waker_thread'] == th) & 
                                (df['waker_tag'] == tag)
                            ]
                            if not match.empty:
                                val = match.iloc[0]['total_dur_ms']
                        write_value_or_empty(ws, row_idx, current_col, val, fmt_sleep_val)
                        current_col += 1
                        
                    # Fill REF
                    for df in all_ref_sleep:
                        val = ""
                        if df is not None:
                            match = df[
                                (df['waker_process'] == proc) & 
                                (df['waker_thread'] == th) & 
                                (df['waker_tag'] == tag)
                            ]
                            if not match.empty:
                                val = match.iloc[0]['total_dur_ms']
                        write_value_or_empty(ws, row_idx, current_col, val, fmt_sleep_val)
                        current_col += 1
                        
                    row_idx += 1


# [NEW] Sleep Attribution Data
    # Lấy khoảng thời gian launch (từ touchDown đến end_ts)
    start_watch = touch_down_ts if touch_down_ts else 0
    end_watch = end_ts if end_ts else (start_watch + 5000000000) # Fallback 5s
    
    if app_tid:
        metrics["Sleep_Waker_Data"] = get_sleep_wakeup_attribution(tp, app_tid, start_watch, end_watch)
    else:
        metrics["Sleep_Waker_Data"] = None


# ---------------------------------------------------------
    # === SLEEP BREAKDOWN BY WAKER (NEW) ===
    # ---------------------------------------------------------
    row_idx += 3
    
    # Formats
    fmt_sleep_header = wb.add_format({"bold": True, "align": "center", "bg_color": "#FFE4C4", "border": 1, "border_color": "#000000"}) # Bisque color
    fmt_sleep_proc = wb.add_format({"bold": True, "align": "left", "bg_color": "#F5F5F5", "border": 1})
    fmt_sleep_thread = wb.add_format({"italic": True, "align": "left", "indent": 1, "border": 1})
    fmt_sleep_tag = wb.add_format({"align": "left", "indent": 2, "border": 1, "font_color": "#333333"})
    fmt_sleep_val = wb.add_format({"num_format": "0.0", "align": "center", "border": 1})

    # [FIXED HERE] Thêm 'if cycle else None' để tránh crash khi cycle bị None
    all_dut_sleep = [cycle.get("Sleep_Waker_Data", None) if cycle else None for cycle in dut_cycles]
    all_ref_sleep = [cycle.get("Sleep_Waker_Data", None) if cycle else None for cycle in ref_cycles]
    
    # Check data
    has_sleep_data = False
    for df in all_dut_sleep + all_ref_sleep:
        if df is not None and not df.empty:
            has_sleep_data = True; break
            
    if has_sleep_data:
        # 1. Header
        ws.merge_range(row_idx, 0, row_idx, 0, "Sleep Woken-By Analysis", fmt_sleep_header)
        col_idx = 1
        for i in range(len(dut_cycles)):
            ws.write(row_idx, col_idx, f"DUT Cy{i+1}", fmt_sleep_header)
            col_idx += 1
        for i in range(len(ref_cycles)):
            ws.write(row_idx, col_idx, f"REF Cy{i+1}", fmt_sleep_header)
            col_idx += 1
        row_idx += 1
        
        ws.write(row_idx, 0, "Waker Process > Thread > Tag", fmt_sleep_header)
        for col in range(1, col_idx): ws.write(row_idx, col, "Dur (ms)", fmt_sleep_header)
        row_idx += 1

        # 2. Aggregate Keys (Process -> Thread -> Tag)
        tree_keys = defaultdict(lambda: defaultdict(set))
        
        for df_list in [all_dut_sleep, all_ref_sleep]:
            for df in df_list:
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        proc = str(row['waker_process'])
                        th = str(row['waker_thread'])
                        tag = str(row['waker_tag'])
                        tree_keys[proc][th].add(tag)
        
        sorted_procs = sorted(tree_keys.keys())
        
        # 3. Draw Table
        for proc in sorted_procs:
            # Draw Process Row
            ws.write(row_idx, 0, proc, fmt_sleep_proc)
            for col in range(1, col_idx): ws.write(row_idx, col, "", fmt_sleep_proc)
            row_idx += 1
            
            sorted_threads = sorted(tree_keys[proc].keys())
            for th in sorted_threads:
                # Draw Thread Row
                ws.write(row_idx, 0, f"Thread: {th}", fmt_sleep_thread)
                for col in range(1, col_idx): ws.write(row_idx, col, "", fmt_sleep_thread)
                row_idx += 1
                
                sorted_tags = sorted(list(tree_keys[proc][th]))
                for tag in sorted_tags:
                    # Draw Tag Row (Data Row)
                    ws.write(row_idx, 0, f"Tag: {tag}", fmt_sleep_tag)
                    current_col = 1
                    
                    # Fill DUT
                    for df in all_dut_sleep:
                        val = ""
                        if df is not None:
                            match = df[
                                (df['waker_process'] == proc) & 
                                (df['waker_thread'] == th) & 
                                (df['waker_tag'] == tag)
                            ]
                            if not match.empty:
                                val = match.iloc[0]['total_dur_ms']
                        write_value_or_empty(ws, row_idx, current_col, val, fmt_sleep_val)
                        current_col += 1
                        
                    # Fill REF
                    for df in all_ref_sleep:
                        val = ""
                        if df is not None:
                            match = df[
                                (df['waker_process'] == proc) & 
                                (df['waker_thread'] == th) & 
                                (df['waker_tag'] == tag)
                            ]
                            if not match.empty:
                                val = match.iloc[0]['total_dur_ms']
                        write_value_or_empty(ws, row_idx, current_col, val, fmt_sleep_val)
                        current_col += 1
                        
                    row_idx += 1