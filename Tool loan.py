import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import plotly.express as px
import json

# --- 0. 設定與連線 ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SHEET_NAME = 'test_piece_db'
JSON_FILE = 'service_account.json'


@st.cache_resource
def connect_google_sheet():
    try:
        if os.path.exists(JSON_FILE):
            creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, SCOPE)
        else:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)
        return sheet
    except Exception as e:
        st.error(f"❌ 連線失敗：{e}")
        st.stop()


sh = connect_google_sheet()
ws_gauges = sh.worksheet('gauges')
ws_logs = sh.worksheet('logs')
ws_users = sh.worksheet('users')


# --- 1. 資料處理核心 ---
@st.cache_data(ttl=60)
def get_all_data(worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_values()

        if not data or len(data) == 0:
            return pd.DataFrame()

        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)

        df.columns = df.columns.map(str).str.strip()
        df = df.loc[:, df.columns != ""]
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ 系統冷卻中，請等待 10 秒後再整理頁面。")
            st.stop()
        else:
            return pd.DataFrame()


def update_db(gauge_id, action, user, machine_no="", val_dict=None, new_status="可借出", note=""):
    now_tw = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    df_g = get_all_data('gauges')
    df_l = get_all_data('logs')

    try:
        g_idx = df_g[df_g['id'].astype(str) == str(gauge_id)].index[0]
        g_row = int(g_idx) + 2
    except:
        st.error(f"找不到編號 {gauge_id}")
        return

    if action == 'borrow':
        curr_note = str(df_g.loc[g_idx, 'note'])
        pre_dict = {}
        if curr_note and curr_note != 'nan':
            # 💡 升級：支援多種分隔符號轉換
            norm_note = curr_note.replace(",", "|").replace("，", "|").replace(";", "|").replace("；", "|")
            for p in norm_note.split("|"):
                if ":" in p:
                    sp = p.split(":", 1)
                    if len(sp) == 2: pre_dict[sp[0].strip()] = sp[1].strip()
        pre_size_json = json.dumps(pre_dict, ensure_ascii=False)

        ws_gauges.update(range_name=f'D{g_row}:F{g_row}', values=[['已借出', user, now_tw]])
        ws_logs.append_row([str(gauge_id), user, machine_no, now_tw, "", pre_size_json, "", "使用中", ""])

    elif action == 'return_request':
        ws_gauges.update(range_name=f'D{g_row}', values=[['待確認']])

        if not df_l.empty and 'gauge_id' in df_l.columns:
            open_sessions = df_l[(df_l['gauge_id'].astype(str) == str(gauge_id)) & (df_l['status'] == '使用中')]
            if not open_sessions.empty:
                l_idx = open_sessions.index[-1]
                l_row = int(l_idx) + 2
                ws_logs.update(range_name=f'H{l_row}', values=[['待驗收']])

    elif action == 'confirm_return':
        val_str = " | ".join([f"{k}:{v}" for k, v in val_dict.items()])
        ws_gauges.update(range_name=f'D{g_row}:G{g_row}', values=[[new_status, '', '', val_str]])

        if not df_l.empty and 'gauge_id' in df_l.columns:
            open_sessions = df_l[
                (df_l['gauge_id'].astype(str) == str(gauge_id)) & (df_l['status'].isin(['使用中', '待驗收']))]
            if not open_sessions.empty:
                l_idx = open_sessions.index[-1]
                l_row = int(l_idx) + 2
                pre_size = str(df_l.loc[l_idx, 'pre_size'])
                post_json = json.dumps(val_dict, ensure_ascii=False)

                ws_logs.update(range_name=f'E{l_row}:H{l_row}', values=[[now_tw, pre_size, post_json, "已結案"]])

    elif action == 'scrap':
        ws_gauges.update(range_name=f'D{g_row}:E{g_row}', values=[['已報廢', '']])
        ws_logs.append_row([str(gauge_id), user, "", now_tw, now_tw, "", "", "已報廢", note])

    get_all_data.clear('gauges')
    get_all_data.clear('logs')


def get_last_sizes(df_logs, gauge_id):
    if df_logs.empty or 'post_size' not in df_logs.columns: return {}
    history = df_logs[(df_logs['gauge_id'].astype(str) == str(gauge_id)) & (df_logs['post_size'] != "")]
    if history.empty: return {}
    last_record = history.sort_values('return_time', ascending=False).iloc[0]
    try:
        return json.loads(last_record['post_size'])
    except:
        return {}


@st.dialog("⚠️ 缺少研磨機號確認")
def confirm_no_machine(gauge_id, current_user):
    st.warning("您目前沒有填寫「研磨機號」。\n\n請問是否確定要直接借出？")
    st.write(f"📍 借出項目： **{gauge_id}**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 確認無機號借出", type="primary", use_container_width=True):
            update_db(gauge_id, 'borrow', current_user, machine_no="無填寫")
            st.rerun()
    with col2:
        if st.button("❌ 取消返回", use_container_width=True):
            st.rerun()


# --- 2. 介面設計 ---
def main():
    st.set_page_config(page_title="標準試磨件管理系統", layout="wide")

    st.markdown("""
        <style>
        .stButton > button { font-size: 18px !important; height: 2.8em !important; width: 100%; border-radius: 6px; }
        .stAlert { padding-top: 0.5rem; padding-bottom: 0.5rem; }
        p, div, label { font-size: 18px !important; }
        </style>
    """, unsafe_allow_html=True)

    df_logs_check = get_all_data('logs')
    if not df_logs_check.empty and 'pre_size' not in df_logs_check.columns:
        st.error(
            "🚨 **【系統架構升級提示】** 🚨\n\n請您前往 Google Sheets 的 `logs` 工作表：\n\n1. 將第一列的標題完全替換為這 9 個欄位：\n`gauge_id`, `user`, `machine`, `borrow_time`, `return_time`, `pre_size`, `post_size`, `status`, `note`")
        st.stop()

    role = st.sidebar.selectbox("切換模式", ["使用者 (操作)", "管理員 (後台)"])

    df_users = get_all_data('users')
    df_g = get_all_data('gauges')
    user_list = df_users['name'].astype(str).tolist() if not df_users.empty else []

    # ==================================
    # 前台：現場操作
    # ==================================
    if role == "使用者 (操作)":
        st.markdown("### ☁️ 標準試磨件借出系統")

        if not user_list:
            st.warning("資料加載中，請稍候...");
            st.stop()

        col_top1, col_top2 = st.columns(2)
        with col_top1:
            current_user = st.selectbox("請先選擇您的姓名", ["--"] + user_list)
        with col_top2:
            current_machine = st.text_input("請輸入研磨機號 (選填)", placeholder="例: EGP26205，若無可留白")

        st.write("")

        user_menu = st.radio("功能選單", ["我要借出 📥", "我要歸還 📤", "查詢狀態 🔍"], horizontal=True,
                             label_visibility="collapsed", key="user_menu_state")

        if user_menu == "我要借出 📥":
            available = df_g[df_g['status'] == '可借出']
            categories = ["全部顯示"] + list(available['category'].unique()) if not available.empty else ["全部顯示"]
            selected_cat = st.selectbox("📁 篩選分類", categories)

            if selected_cat != "全部顯示":
                available = available[available['category'] == selected_cat]

            st.markdown("#### ✅ 庫存試磨件")

            if available.empty:
                st.info("此分類目前無可借出項目")
            else:
                for _, row in available.iterrows():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.info(
                            f"📍 **{row['category']}** | {row['id']} | 📏 目前尺寸: {row['note'] if row['note'] else '無'}")
                    with col2:
                        if st.button("借出", key=f"br_{row['id']}"):
                            if current_user == "--":
                                st.error("⚠️ 請先在畫面上方選擇您的「姓名」！")
                            elif not current_machine.strip():
                                confirm_no_machine(row['id'], current_user)
                            else:
                                update_db(row['id'], 'borrow', current_user, machine_no=current_machine.strip())
                                st.success(f"{row['id']} 借出成功！")
                                st.rerun()

        elif user_menu == "我要歸還 📤":
            borrowed = df_g[df_g['status'].isin(['已借出', '待確認'])]
            st.markdown("#### 📤 借出狀態")

            if current_user == "--":
                st.info("💡 請在畫面上方選擇您的「姓名」，以解鎖您的歸還項目。")

            if borrowed.empty:
                st.info("目前無借出項目")
            else:
                for _, row in borrowed.iterrows():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        if row['status'] == '待確認':
                            st.warning(
                                f"⏳ **{row['category']}** | {row['id']} - 持有人: {row['current_user']} (品保驗收中)")
                        else:
                            st.success(f"✅ **{row['category']}** | {row['id']} - 持有人: {row['current_user']}")
                    with col2:
                        if row['status'] == '待確認':
                            st.button("等待中", key=f"wait_{row['id']}", disabled=True)
                        else:
                            if str(row['current_user']) == current_user:
                                if st.button("申請歸還", key=f"rt_{row['id']}"):
                                    update_db(row['id'], 'return_request', current_user)
                                    st.rerun()
                            else:
                                st.button("非本人", key=f"dis_{row['id']}", disabled=True)

        elif user_menu == "查詢狀態 🔍":
            st.dataframe(df_g[['id', 'category', 'status', 'current_user']], use_container_width=True, hide_index=True)

    # ==================================
    # 後台：品保管理
    # ==================================
    else:
        st.header("⚙️ 品保管理後台")
        if st.sidebar.text_input("管理密碼", type="password") == "0000":
            df_logs = get_all_data('logs')

            admin_menu_opts = ["✅ 歸還驗收", "📋 尺寸總表", "📉 磨耗分析", "📊 數據統計", "🗑️ 報廢汰換",
                               "📝 事件總紀錄", "⚙️ 系統設定"]
            admin_menu = st.radio("後台選單", admin_menu_opts, horizontal=True, label_visibility="collapsed",
                                  key="admin_menu_state")

            # --- 1. 歸還驗收 ---
            if admin_menu == "✅ 歸還驗收":
                pending = df_g[df_g['status'] == '待確認']
                if pending.empty:
                    st.success("🎉 目前暫無待驗收項目")
                for _, row in pending.iterrows():
                    with st.expander(f"📦 編號: {row['id']} | 借用人: {row['current_user']}", expanded=True):
                        m_info = "無紀錄"
                        if not df_logs.empty and 'gauge_id' in df_logs.columns:
                            open_sessions = df_logs[
                                (df_logs['gauge_id'].astype(str) == str(row['id'])) & (df_logs['status'] == '待驗收')]
                            if not open_sessions.empty:
                                m_info = open_sessions['machine'].values[-1]

                        st.write(f"品項: **{row['category']}** | 使用機台: **{m_info}**")

                        with st.form(key=f"f_v_{row['id']}"):
                            raw_specs = str(row['spec']).split(",") if row['spec'] else []
                            regions_info = {}
                            for s in raw_specs:
                                s = s.strip()
                                if "=" in s:
                                    split_res = s.split("=", 1)
                                    if len(split_res) == 2:
                                        k, v = split_res
                                        try:
                                            regions_info[k.strip()] = float(v.strip())
                                        except:
                                            regions_info[k.strip()] = None
                                else:
                                    if s: regions_info[s] = None

                            if not regions_info: regions_info = {"尺寸數值": None}
                            last_sizes = get_last_sizes(df_logs, row['id'])

                            measured_vals = {}
                            cols = st.columns(len(regions_info))
                            for idx, (reg, target) in enumerate(regions_info.items()):
                                prev_val = last_sizes.get(reg, "無紀錄")
                                target_text = f"{target}" if target is not None else "未設定"
                                cols[idx].caption(f"🎯 標準: {target_text} | 🔄 上次: {prev_val}")
                                try:
                                    default_val = float(prev_val)
                                except:
                                    default_val = float(target) if target is not None else 0.0
                                measured_vals[reg] = cols[idx].number_input(f"實測 {reg}", format="%.3f",
                                                                            value=default_val)

                            if st.form_submit_button("確認尺寸並結案", type="primary"):
                                is_scrap = False
                                for reg, val in measured_vals.items():
                                    target = regions_info.get(reg)
                                    if target is not None and abs(target - val) >= 5.0:
                                        is_scrap = True;
                                        break
                                final_status = "需汰換" if is_scrap else "可借出"
                                update_db(row['id'], 'confirm_return', row['current_user'], val_dict=measured_vals,
                                          new_status=final_status)
                                st.rerun()

            # --- 2. 尺寸總表 (✨ 萬能標點符號解析版) ---
            elif admin_menu == "📋 尺寸總表":
                st.subheader("📋 試磨件當前尺寸總表")
                if not df_g.empty:
                    summary_data = []
                    active_df = df_g[df_g['status'] != '已報廢']

                    for _, row in active_df.iterrows():
                        raw_specs = str(row['spec']).split(",") if row['spec'] else []
                        regions_info = {}
                        for s in raw_specs:
                            s = s.strip()
                            if "=" in s:
                                split_res = s.split("=", 1)
                                if len(split_res) == 2:
                                    k, v = split_res
                                    try:
                                        regions_info[k.strip()] = float(v.strip())
                                    except:
                                        pass

                        raw_note = str(row['note']).strip() if row['note'] else ""
                        current_vals = {}

                        if raw_note:
                            # 💡 萬能轉換：把逗號、全形逗號、分號全部轉成系統看得懂的直柱 |
                            norm_note = raw_note.replace(",", "|").replace("，", "|").replace(";", "|").replace("；", "|")
                            parts = norm_note.split("|")
                            for p in parts:
                                if ":" in p:
                                    split_res = p.split(":", 1)
                                    if len(split_res) == 2:
                                        k, v = split_res
                                        try:
                                            current_vals[k.strip()] = float(v.strip())
                                        except:
                                            pass

                        overall_judgment = "繼續使用"
                        for reg, target in regions_info.items():
                            curr = current_vals.get(reg, None)

                            # 防呆：如果只有一個測量部位，且抓不到特定標籤，就把整段純數字當作現值
                            if curr is None and not current_vals and len(regions_info) == 1 and raw_note:
                                try:
                                    curr = float(raw_note)
                                except:
                                    pass

                            if curr is not None:
                                remain = 5.0 - abs(target - curr) if target is not None else 0
                                judge = "合格" if remain > 0 else "NG"
                                if judge == "NG": overall_judgment = "需汰換"
                                summary_data.append({
                                    "品項 (編號)": f"{row['category']} ({row['id']})",
                                    "部位": reg,
                                    "狀態": row['status'],
                                    "目標值": target if target is not None else "-",
                                    "現值": f"{curr:.3f}",
                                    "剩餘研磨量": f"{remain:.3f}" if target is not None else "-",
                                    "判斷": judge if target is not None else "-"
                                })
                            else:
                                # 💡 顯示防呆：多部位測量時，若缺少資料顯示無對應紀錄，避免版面炸裂
                                display_val = raw_note if (len(regions_info) == 1 and raw_note) else "無對應紀錄"
                                summary_data.append({
                                    "品項 (編號)": f"{row['category']} ({row['id']})",
                                    "部位": reg,
                                    "狀態": row['status'],
                                    "目標值": target if target is not None else "-",
                                    "現值": display_val if raw_note else "無紀錄",
                                    "剩餘研磨量": "-",
                                    "判斷": "-"
                                })

                    if summary_data:
                        df_summary = pd.DataFrame(summary_data)

                        def highlight_ng(val):
                            return f'background-color: #ffcccc' if val in ['NG', '需汰換'] else ''

                        st.dataframe(df_summary.style.applymap(highlight_ng, subset=['判斷', '狀態']),
                                     use_container_width=True, hide_index=True)

            # --- 3. 磨耗追蹤 ---
            elif admin_menu == "📉 磨耗分析":
                st.subheader("📉 單次借用事件磨耗分析")
                if not df_g.empty and not df_logs.empty and 'post_size' in df_logs.columns:
                    opts = ["全部顯示"] + df_g['id'].astype(str).tolist()
                    target_id = st.selectbox("🔍 選擇要查詢的試磨件編號", opts)

                    valid_events = df_logs[df_logs['status'] == '已結案']
                    if target_id != "全部顯示":
                        valid_events = valid_events[valid_events['gauge_id'].astype(str) == str(target_id)]

                    if not valid_events.empty:
                        wear_data = []
                        for idx, row in valid_events.iterrows():
                            try:
                                pre_dict = json.loads(row['pre_size']) if row['pre_size'] else {}
                                post_dict = json.loads(row['post_size']) if row['post_size'] else {}

                                for reg, post_val in post_dict.items():
                                    pre_val = pre_dict.get(reg, post_val)
                                    wear_amt = float(pre_val) - float(post_val)
                                    wear_data.append({
                                        "編號": row['gauge_id'],
                                        "借用人": row['user'],
                                        "使用機台": row['machine'],
                                        "借出時間": row['borrow_time'],
                                        "歸還時間": row['return_time'],
                                        "測量部位": reg,
                                        "出庫尺寸": float(pre_val),
                                        "入庫尺寸": float(post_val),
                                        "單次磨掉量": float(f"{wear_amt:.3f}")
                                    })
                            except:
                                continue

                        if wear_data:
                            wear_df = pd.DataFrame(wear_data).sort_values('借出時間', ascending=False)
                            st.dataframe(wear_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("無法解析此區間的歷史尺寸。")
                    else:
                        st.info("尚無完整的歷史尺寸紀錄。")

            # --- 4. 數據統計 ---
            elif admin_menu == "📊 數據統計":
                st.subheader("📊 借出頻率與使用量統計")
                if not df_logs.empty and 'borrow_time' in df_logs.columns:
                    borrow_logs = df_logs[df_logs['borrow_time'] != ""].copy()
                    if not borrow_logs.empty:
                        borrow_logs['date'] = pd.to_datetime(borrow_logs['borrow_time']).dt.date
                        min_date = borrow_logs['date'].min()
                        max_date = borrow_logs['date'].max()

                        col_date1, col_date2 = st.columns(2)
                        with col_date1:
                            start_date = st.date_input("起始日期", min_date, min_value=min_date, max_value=max_date)
                        with col_date2:
                            end_date = st.date_input("結束日期", max_date, min_value=min_date, max_value=max_date)

                        mask = (borrow_logs['date'] >= start_date) & (borrow_logs['date'] <= end_date)
                        filtered_logs = borrow_logs[mask]

                        if not filtered_logs.empty:
                            user_counts = filtered_logs['user'].value_counts().reset_index()
                            user_counts.columns = ['人員', '借出總次數']
                            st.plotly_chart(px.bar(user_counts, x='人員', y='借出總次數', title='👤 人員借用活躍度排行',
                                                   text_auto=True, color='借出總次數', color_continuous_scale='Blues'),
                                            use_container_width=True)

                            item_counts = filtered_logs['gauge_id'].value_counts().reset_index()
                            item_counts.columns = ['試磨件編號', '被借出次數']
                            st.plotly_chart(
                                px.bar(item_counts, x='試磨件編號', y='被借出次數', title='🔥 試磨件熱門排行 (周轉率)',
                                       text_auto=True, color='被借出次數', color_continuous_scale='Teal'),
                                use_container_width=True)
                        else:
                            st.info("此區間無紀錄。")
                    else:
                        st.info("無借出紀錄。")

            # --- 5. 報廢汰換 ---
            elif admin_menu == "🗑️ 報廢汰換":
                st.subheader("🗑️ 試磨件報廢與汰換作業")
                active_items = df_g[df_g['status'] != '已報廢']

                if not active_items.empty:
                    scrap_candidates = active_items[active_items['status'] == '需汰換']
                    if not scrap_candidates.empty:
                        st.warning(f"⚠️ 系統偵測到有 {len(scrap_candidates)} 個試磨件已達汰換標準，建議盡速處理！")

                    opts = active_items.apply(lambda x: f"{x['id']} - {x['category']} (狀態: {x['status']})",
                                              axis=1).tolist()
                    sel_item = st.selectbox("請選擇要執行報廢的試磨件", ["-- 請選擇 --"] + opts)

                    if sel_item != "-- 請選擇 --":
                        target_id = sel_item.split(" - ")[0]
                        scrap_note = st.text_input("📝 報廢原因 / 備註 (必填)",
                                                   placeholder="例如：磨損超過5mm容許值，依規定報廢")

                        if st.button("🚨 確認報廢", type="primary"):
                            if scrap_note.strip():
                                update_db(target_id, 'scrap', "品保管理員", note=scrap_note)
                                st.success(f"✅ 編號 {target_id} 已成功報廢！")
                                st.rerun()
                            else:
                                st.error("⚠️ 為了後續追蹤，請務必填寫報廢原因！")
                else:
                    st.info("目前無可報廢的試磨件。")

            # --- 6. 事件總紀錄 ---
            elif admin_menu == "📝 事件總紀錄":
                st.write("📊 這裡呈現的是完整的週期事件 (每個橫列代表一次借用~歸還的資訊)")
                st.dataframe(df_logs, use_container_width=True)

            # --- 7. 系統基本設定 ---
            elif admin_menu == "⚙️ 系統設定":
                st.subheader("⚙️ 系統基本資料維護")
                st.write("無需開啟 Google Sheet，您可直接在此新增人員或將新購買的試磨件入庫。")

                col_sys1, col_sys2 = st.columns(2)

                with col_sys1:
                    st.markdown("#### 👤 人員增減")
                    with st.container(border=True):
                        new_user = st.text_input("➕ 新增人員姓名", placeholder="請輸入全名")
                        if st.button("新增人員"):
                            if new_user.strip() and new_user not in user_list:
                                ws_users.append_row([new_user.strip()])
                                get_all_data.clear('users')
                                st.success(f"✅ 已成功新增人員：{new_user}")
                                st.rerun()
                            elif new_user in user_list:
                                st.error("⚠️ 該人員已經存在名單中！")
                            else:
                                st.error("⚠️ 姓名不能為空白！")

                        st.divider()
                        del_user = st.selectbox("➖ 刪除人員 (離職/轉調)", ["-- 請選擇 --"] + user_list)
                        if st.button("刪除此人員", type="primary"):
                            if del_user != "-- 請選擇 --":
                                try:
                                    row_idx = int(df_users[df_users['name'].astype(str) == str(del_user)].index[0]) + 2
                                    ws_users.delete_rows(row_idx)
                                    get_all_data.clear('users')
                                    st.success(f"🗑️ 已成功刪除人員：{del_user}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"刪除失敗: {e}")
                            else:
                                st.error("⚠️ 請先選擇要刪除的人員！")

                with col_sys2:
                    st.markdown("#### 📦 新品試磨件入庫")
                    with st.container(border=True):
                        with st.form("add_gauge_form"):
                            new_id = st.text_input("1. 試磨件編號 (必填，不可重複)", placeholder="例如: 25-短軸-E")
                            new_cat = st.text_input("2. 品項名稱 (必填)", placeholder="例如: 25 短軸E")
                            new_spec = st.text_input("3. 測量規格與目標值 (選填)",
                                                     placeholder="例如: OD40(短)=40, OD50=50")
                            st.caption("💡 規格請嚴格遵守 `部位名稱=目標值`，多個部位請用 `,` 隔開。")

                            if st.form_submit_button("➕ 確認新品入庫", type="primary"):
                                if new_id.strip() and new_cat.strip():
                                    if str(new_id) in df_g['id'].astype(str).tolist():
                                        st.error("⚠️ 此「編號」已經存在於系統中，請確認是否打錯或是更改新編號！")
                                    else:
                                        ws_gauges.append_row(
                                            [new_id.strip(), new_cat.strip(), new_spec.strip(), "可借出", "", "", ""])
                                        get_all_data.clear('gauges')
                                        st.success(f"✅ 新品 {new_id} 已成功加入庫存，現場可立即借用！")
                                        st.rerun()
                                else:
                                    st.error("⚠️ 「編號」與「品項名稱」為必填欄位！")
        else:
            st.warning("🔒 請輸入密碼")


if __name__ == "__main__":
    main()
