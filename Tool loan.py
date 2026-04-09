import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import plotly.express as px
import json
import streamlit.components.v1 as components

# ==========================================
# 🌐 語言翻譯辭典庫 (i18n) - 正名回歸版
# ==========================================
LANG_DICT = {
    "zh": {
        "sidebar_role": "請選擇您的身份",
        "role_user": "使用者 (操作)",
        "role_admin": "管理員 (後台)",
        "sidebar_lang": "Language / 語言",
        "app_title": "☁️ 標準試磨件借出系統",  # 💡 改回原名
        "loading": "資料加載中，請稍候...",
        "sel_name": "請先選擇您的姓名",
        "sel_machine": "請輸入研磨機號 (選填)",
        "ph_machine": "例: EGP26205，若無可留白",
        "tab_borrow": "我要借出 📥",
        "tab_return": "我要歸還 📤",
        "tab_status": "查詢狀態 🔍",
        "filter_cat": "📁 篩選分類",
        "all_cat": "全部顯示",
        "stock_title": "#### ✅ 庫存試磨件",  # 💡 改回原名
        "no_stock": "此分類目前無可借出項目",
        "btn_borrow": "借出",
        "err_name": "⚠️ 請先在畫面上方選擇您的「姓名」！",
        "msg_borrowed": "借出成功！",
        "borrowed_title": "#### 📤 借出狀態",
        "no_borrowed": "目前無借出項目",
        "tip_name": "💡 請在畫面上方選擇您的「姓名」，以解鎖您的歸還項目。",
        "status_qa": "品保驗收中",
        "status_holder": "持有人",
        "btn_wait": "等待中",
        "btn_return": "申請歸還",
        "btn_not_yours": "非本人",
        "dlg_warn": "您目前沒有填寫「研磨機號」。\n\n請問是否確定要直接借出？",
        "dlg_item": "📍 借出項目：",
        "btn_dlg_confirm": "✅ 確認無機號借出",
        "btn_dlg_cancel": "❌ 取消返回",
        "admin_title": "⚙️ 品保管理後台",
        "admin_pwd": "管理密碼",
        "admin_err_pwd": "🔒 請輸入密碼",
        "btn_sync": "🔄 強制同步最新資料",
        "msg_sync": "✅ 資料已同步！",
        "menu_qa": "✅ 歸還驗收",
        "menu_list": "📋 尺寸總表",
        "menu_wear": "📉 磨耗分析",
        "menu_stats": "📊 數據統計",
        "menu_scrap": "🗑️ 報廢汰換",
        "menu_logs": "📝 事件總紀錄",
        "menu_sys": "⚙️ 系統設定",
        "db_可借出": "可借出",
        "db_已借出": "已借出",
        "db_待確認": "待確認",
        "db_需汰換": "需汰換",
        "db_已報廢": "已報廢",
        "col_id": "編號",
        "col_cat": "品項",
        "col_status": "狀態",
        "col_user": "使用者",
        "col_target": "目標值",
        "col_current": "現值",
        "col_remain": "剩餘研磨量",
        "col_judge": "判斷",
        "judge_pass": "合格",
        "judge_fail": "需汰換",
        "measure_val": "實測",
        "btn_confirm_return": "確認尺寸並結案",
        "no_qa_items": "🎉 目前暫無待驗收項目",
        "wear_all": "全部顯示",
        "wear_sel": "🔍 選擇要查詢的試磨件編號",
        "stat_start": "起始日期",
        "stat_end": "結束日期",
        "stat_user_title": "👤 人員借用活躍度排行",
        "stat_item_title": "🔥 試磨件熱門排行 (周轉率)",
        "stat_no_data": "此區間無紀錄。",
        "scrap_warn": "⚠️ 系統偵測到有 {} 個試磨件已達汰換標準，建議盡速處理！",
        "scrap_sel": "請選擇要執行報廢的試磨件",
        "scrap_ph": "-- 請選擇 --",
        "scrap_note": "📝 報廢原因 / 備註 (必填)",
        "scrap_btn": "🚨 確認報廢",
        "scrap_err": "⚠️ 為了後續追蹤，請務必填寫報廢原因！",
        "sys_user_add": "#### 👤 人員增減",
        "sys_user_name": "➕ 新增人員姓名",
        "sys_btn_add": "新增人員",
        "sys_user_del": "➖ 刪除人員 (離職/轉調)",
        "sys_btn_del": "刪除此人員",
        "sys_item_add": "#### 📦 新品試磨件入庫",
        "sys_item_id": "1. 試磨件編號 (必填，不可重複)",
        "sys_item_name": "2. 品項名稱 (必填)",
        "sys_item_spec": "3. 測量規格與目標值 (選填)",
        "sys_btn_item": "➕ 確認新品入庫"
    },
    "en": {
        "sidebar_role": "Select Your Role",
        "role_user": "User (Operation)",
        "role_admin": "Admin (Backend)",
        "sidebar_lang": "Language / 語言",
        "app_title": "☁️ Standard Test Piece System",  # 💡 英文也同步正名
        "loading": "Loading data, please wait...",
        "sel_name": "Please select your name",
        "sel_machine": "Machine No. (Optional)",
        "ph_machine": "e.g. EGP26205, or leave blank",
        "tab_borrow": "Borrow 📥",
        "tab_return": "Return 📤",
        "tab_status": "Status 🔍",
        "filter_cat": "📁 Category Filter",
        "all_cat": "All Categories",
        "stock_title": "#### ✅ Available Test Pieces",  # 💡 英文也同步正名
        "no_stock": "No items available in this category.",
        "btn_borrow": "Borrow",
        "err_name": "⚠️ Please select your name at the top first!",
        "msg_borrowed": "borrowed successfully!",
        "borrowed_title": "#### 📤 Borrowed Status",
        "no_borrowed": "No items borrowed currently.",
        "tip_name": "💡 Select your name above to unlock your return items.",
        "status_qa": "Pending QA",
        "status_holder": "Holder",
        "btn_wait": "Waiting",
        "btn_return": "Return",
        "btn_not_yours": "Not Yours",
        "dlg_warn": "You have not entered a Machine No.\n\nAre you sure you want to proceed?",
        "dlg_item": "📍 Borrowing Item: ",
        "btn_dlg_confirm": "✅ Confirm Borrow",
        "btn_dlg_cancel": "❌ Cancel",
        "admin_title": "⚙️ QA Admin Dashboard",
        "admin_pwd": "Admin Password",
        "admin_err_pwd": "🔒 Please enter password",
        "btn_sync": "🔄 Sync Latest Data",
        "msg_sync": "✅ Data Synchronized!",
        "menu_qa": "✅ QA Checks",
        "menu_list": "📋 Master List",
        "menu_wear": "📉 Wear Analysis",
        "menu_stats": "📊 Statistics",
        "menu_scrap": "🗑️ Scrapping",
        "menu_logs": "📝 All Logs",
        "menu_sys": "⚙️ Settings",
        "db_可借出": "Available",
        "db_已借出": "Borrowed",
        "db_待確認": "Pending QA",
        "db_需汰換": "Replace",
        "db_已報廢": "Scrapped",
        "col_id": "ID",
        "col_cat": "Category",
        "col_status": "Status",
        "col_user": "User",
        "col_target": "Target",
        "col_current": "Current",
        "col_remain": "Remaining",
        "col_judge": "Judgment",
        "judge_pass": "Pass",
        "judge_fail": "Replace",
        "measure_val": "Measure",
        "btn_confirm_return": "Confirm & Close Case",
        "no_qa_items": "🎉 No items pending QA currently.",
        "wear_all": "All",
        "wear_sel": "🔍 Select Test Piece ID",
        "stat_start": "Start Date",
        "stat_end": "End Date",
        "stat_user_title": "👤 Top Users",
        "stat_item_title": "🔥 Top Borrowed Items",
        "stat_no_data": "No records found in this period.",
        "scrap_warn": "⚠️ {} items need replacement!",
        "scrap_sel": "Select item to scrap",
        "scrap_ph": "-- Select --",
        "scrap_note": "📝 Reason for scrapping (Required)",
        "scrap_btn": "🚨 Confirm Scrap",
        "scrap_err": "⚠️ Please provide a reason!",
        "sys_user_add": "#### 👤 Add/Remove User",
        "sys_user_name": "➕ New User Name",
        "sys_btn_add": "Add User",
        "sys_user_del": "➖ Remove User",
        "sys_btn_del": "Remove",
        "sys_item_add": "#### 📦 Add New Test Piece",
        "sys_item_id": "1. Test Piece ID (Unique)",
        "sys_item_name": "2. Category Name",
        "sys_item_spec": "3. Specs & Targets (Optional)",
        "sys_btn_item": "➕ Add Test Piece"
    }
}


# 取得翻譯小幫手
def t(key):
    lang = st.session_state.get('lang', 'zh')
    return LANG_DICT[lang].get(key, key)


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
        st.error(f"❌ 連線失敗/Connection Error：{e}")
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
        if not data or len(data) == 0: return pd.DataFrame()
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df.columns = df.columns.map(str).str.strip()
        df = df.loc[:, df.columns != ""]
        df = df.loc[:, ~df.columns.duplicated()]
        return df
    except Exception as e:
        if "429" in str(e):
            st.warning("⚠️ 系統冷卻中 / System cooling down. Wait 10s.")
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
        return
    if action == 'borrow':
        curr_note = str(df_g.loc[g_idx, 'note'])
        pre_dict = {}
        if curr_note and curr_note != 'nan':
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


@st.dialog("⚠️ 缺少研磨機號確認 / Warning")
def confirm_no_machine(gauge_id, current_user):
    st.warning(t('dlg_warn'))
    st.write(f"{t('dlg_item')} **{gauge_id}**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t('btn_dlg_confirm'), type="primary", use_container_width=True):
            update_db(gauge_id, 'borrow', current_user, machine_no="無填寫")
            st.rerun()
    with col2:
        if st.button(t('btn_dlg_cancel'), use_container_width=True):
            st.rerun()


# --- 2. 介面設計 ---
def main():
    st.set_page_config(page_title="標準試磨件管理系統", layout="wide")

    # 手機鍵盤封印腳本
    components.html(
        """
        <script>
        const doc = window.parent.document;
        function disableMobileKeyboard() {
            const inputs = doc.querySelectorAll('div[data-baseweb="select"] input');
            inputs.forEach(input => {
                input.setAttribute('inputmode', 'none');
                input.setAttribute('readonly', 'true');
            });
        }
        disableMobileKeyboard();
        const observer = new MutationObserver(disableMobileKeyboard);
        observer.observe(doc.body, {childList: true, subtree: true});
        </script>
        """, height=0, width=0
    )

    st.markdown("""
        <style>
        .stButton > button { font-size: 18px !important; height: 2.8em !important; width: 100%; border-radius: 6px; }
        .stAlert { padding-top: 0.5rem; padding-bottom: 0.5rem; }
        p, div, label { font-size: 18px !important; }
        div[data-baseweb="select"] input { caret-color: transparent !important; cursor: pointer !important; }
        </style>
    """, unsafe_allow_html=True)

    df_logs_check = get_all_data('logs')
    if not df_logs_check.empty and 'pre_size' not in df_logs_check.columns:
        st.stop()

    # 🌐 語言切換區
    st.sidebar.markdown(f"**{t('sidebar_lang')}**")
    lang_selection = st.sidebar.radio("Lang", ["中文", "English"], label_visibility="collapsed", horizontal=True)
    st.session_state['lang'] = 'zh' if lang_selection == "中文" else 'en'

    st.sidebar.divider()

    role_opts = [t('role_user'), t('role_admin')]
    role = st.sidebar.selectbox(t('sidebar_role'), role_opts)

    df_users = get_all_data('users')
    df_g = get_all_data('gauges')
    user_list = df_users['name'].astype(str).tolist() if not df_users.empty else []

    # ==================================
    # 前台：現場操作
    # ==================================
    if role == t('role_user'):
        st.markdown(f"### {t('app_title')}")

        if not user_list:
            st.warning(t('loading'));
            st.stop()

        col_top1, col_top2 = st.columns(2)
        with col_top1:
            current_user = st.selectbox(t('sel_name'), ["--"] + user_list)
        with col_top2:
            current_machine = st.text_input(t('sel_machine'), placeholder=t('ph_machine'))

        st.write("")

        menu_opts = [t('tab_borrow'), t('tab_return'), t('tab_status')]
        user_menu = st.radio("Menu", menu_opts, horizontal=True, label_visibility="collapsed", key="user_menu_state")

        if user_menu == t('tab_borrow'):
            available = df_g[df_g['status'] == '可借出']
            categories = [t('all_cat')] + list(available['category'].unique()) if not available.empty else [
                t('all_cat')]
            selected_cat = st.selectbox(t('filter_cat'), categories)

            if selected_cat != t('all_cat'):
                available = available[available['category'] == selected_cat]

            st.markdown(t('stock_title'))

            if available.empty:
                st.info(t('no_stock'))
            else:
                for _, row in available.iterrows():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.info(f"📍 **{row['category']}** | {row['id']} | 📏 : {row['note'] if row['note'] else '-'}")
                    with col2:
                        if st.button(t('btn_borrow'), key=f"br_{row['id']}"):
                            if current_user == "--":
                                st.error(t('err_name'))
                            elif not current_machine.strip():
                                confirm_no_machine(row['id'], current_user)
                            else:
                                update_db(row['id'], 'borrow', current_user, machine_no=current_machine.strip())
                                st.success(f"{row['id']} {t('msg_borrowed')}")
                                st.rerun()

        elif user_menu == t('tab_return'):
            borrowed = df_g[df_g['status'].isin(['已借出', '待確認'])]
            st.markdown(t('borrowed_title'))

            if current_user == "--":
                st.info(t('tip_name'))

            if borrowed.empty:
                st.info(t('no_borrowed'))
            else:
                for _, row in borrowed.iterrows():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        if row['status'] == '待確認':
                            st.warning(
                                f"⏳ **{row['category']}** | {row['id']} - {t('status_holder')}: {row['current_user']} ({t('status_qa')})")
                        else:
                            st.success(
                                f"✅ **{row['category']}** | {row['id']} - {t('status_holder')}: {row['current_user']}")
                    with col2:
                        if row['status'] == '待確認':
                            st.button(t('btn_wait'), key=f"wait_{row['id']}", disabled=True)
                        else:
                            if str(row['current_user']) == current_user:
                                if st.button(t('btn_return'), key=f"rt_{row['id']}"):
                                    update_db(row['id'], 'return_request', current_user)
                                    st.rerun()
                            else:
                                st.button(t('btn_not_yours'), key=f"dis_{row['id']}", disabled=True)

        elif user_menu == t('tab_status'):
            disp_df = df_g[['id', 'category', 'status', 'current_user']].copy()
            disp_df.rename(columns={'id': t('col_id'), 'category': t('col_cat'), 'status': t('col_status'),
                                    'current_user': t('col_user')}, inplace=True)
            disp_df[t('col_status')] = disp_df[t('col_status')].apply(lambda x: t(f"db_{x}"))
            st.dataframe(disp_df, use_container_width=True, hide_index=True)

    # ==================================
    # 後台：品保管理
    # ==================================
    else:
        st.header(t('admin_title'))
        if st.sidebar.text_input(t('admin_pwd'), type="password") == "0000":

            if st.sidebar.button(t('btn_sync'), use_container_width=True):
                get_all_data.clear('gauges')
                get_all_data.clear('logs')
                get_all_data.clear('users')
                st.success(t('msg_sync'))
                st.rerun()

            df_logs = get_all_data('logs')

            admin_menu_opts = [t('menu_qa'), t('menu_list'), t('menu_wear'), t('menu_stats'), t('menu_scrap'),
                               t('menu_logs'), t('menu_sys')]
            admin_menu = st.radio("Admin Menu", admin_menu_opts, horizontal=True, label_visibility="collapsed",
                                  key="admin_menu_state")

            # --- 1. 歸還驗收 ---
            if admin_menu == t('menu_qa'):
                pending = df_g[df_g['status'] == '待確認']
                if pending.empty:
                    st.success(t('no_qa_items'))
                for _, row in pending.iterrows():
                    with st.expander(f"📦 {t('col_id')}: {row['id']} | {t('col_user')}: {row['current_user']}",
                                     expanded=True):
                        m_info = "-"
                        if not df_logs.empty and 'gauge_id' in df_logs.columns:
                            open_sessions = df_logs[
                                (df_logs['gauge_id'].astype(str) == str(row['id'])) & (df_logs['status'] == '待驗收')]
                            if not open_sessions.empty:
                                m_info = open_sessions['machine'].values[-1]

                        st.write(f"{t('col_cat')}: **{row['category']}** | Machine: **{m_info}**")

                        with st.form(key=f"f_v_{row['id']}"):
                            raw_specs = str(row['spec']).split(",") if row['spec'] else []
                            regions_info = {}
                            for s in raw_specs:
                                s = s.strip()
                                if "=" in s:
                                    split_res = s.split("=", 1)
                                    if len(split_res) == 2:
                                        try:
                                            regions_info[split_res[0].strip()] = float(split_res[1].strip())
                                        except:
                                            regions_info[split_res[0].strip()] = None
                                else:
                                    if s: regions_info[s] = None

                            if not regions_info: regions_info = {"Value": None}
                            last_sizes = get_last_sizes(df_logs, row['id'])

                            measured_vals = {}
                            cols = st.columns(len(regions_info))
                            for idx, (reg, target) in enumerate(regions_info.items()):
                                prev_val = last_sizes.get(reg, "-")
                                target_text = f"{target}" if target is not None else "-"
                                cols[idx].caption(f"🎯 Target: {target_text} | 🔄 Prev: {prev_val}")
                                try:
                                    default_val = float(prev_val)
                                except:
                                    default_val = float(target) if target is not None else 0.0
                                measured_vals[reg] = cols[idx].number_input(f"{t('measure_val')} {reg}", format="%.3f",
                                                                            value=default_val)

                            if st.form_submit_button(t('btn_confirm_return'), type="primary"):
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

            # --- 2. 尺寸總表 ---
            elif admin_menu == t('menu_list'):
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
                                    try:
                                        regions_info[split_res[0].strip()] = float(split_res[1].strip())
                                    except:
                                        pass

                        raw_note = str(row['note']).strip() if row['note'] else ""
                        current_vals = {}
                        if raw_note:
                            norm_note = raw_note.replace(",", "|").replace("，", "|").replace(";", "|").replace("；", "|")
                            for p in norm_note.split("|"):
                                if ":" in p:
                                    split_res = p.split(":", 1)
                                    if len(split_res) == 2:
                                        try:
                                            current_vals[split_res[0].strip()] = float(split_res[1].strip())
                                        except:
                                            pass

                        for reg, target in regions_info.items():
                            curr = current_vals.get(reg, None)
                            if curr is None and not current_vals and len(regions_info) == 1 and raw_note:
                                try:
                                    curr = float(raw_note)
                                except:
                                    pass

                            if curr is not None:
                                remain = 5.0 - abs(target - curr) if target is not None else 0
                                judge = t('judge_pass') if remain > 0 else t('judge_fail')
                                summary_data.append({
                                    t('col_cat'): f"{row['category']} ({row['id']})",
                                    "Part": reg,
                                    t('col_status'): t(f"db_{row['status']}"),
                                    t('col_target'): target if target is not None else "-",
                                    t('col_current'): f"{curr:.3f}",
                                    t('col_remain'): f"{remain:.3f}" if target is not None else "-",
                                    t('col_judge'): judge if target is not None else "-"
                                })
                            else:
                                display_val = raw_note if (len(regions_info) == 1 and raw_note) else "-"
                                summary_data.append({
                                    t('col_cat'): f"{row['category']} ({row['id']})",
                                    "Part": reg,
                                    t('col_status'): t(f"db_{row['status']}"),
                                    t('col_target'): target if target is not None else "-",
                                    t('col_current'): display_val if raw_note else "-",
                                    t('col_remain'): "-",
                                    t('col_judge'): "-"
                                })

                    if summary_data:
                        df_summary = pd.DataFrame(summary_data)

                        def highlight_ng(val):
                            return f'background-color: #ffcccc' if val in [t('judge_fail'), t('db_需汰換')] else ''

                        st.dataframe(df_summary.style.map(highlight_ng, subset=[t('col_judge'), t('col_status')]),
                                     use_container_width=True, hide_index=True)

            # --- 3. 磨耗追蹤 ---
            elif admin_menu == t('menu_wear'):
                st.subheader(t('menu_wear'))
                if not df_g.empty and not df_logs.empty and 'post_size' in df_logs.columns:
                    opts = [t('wear_all')] + df_g['id'].astype(str).tolist()
                    target_id = st.selectbox(t('wear_sel'), opts)
                    valid_events = df_logs[df_logs['status'] == '已結案']
                    if target_id != t('wear_all'):
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
                                        t('col_id'): row['gauge_id'], t('col_user'): row['user'],
                                        "Machine": row['machine'],
                                        "Borrow Time": row['borrow_time'], "Return Time": row['return_time'],
                                        "Part": reg, "Pre-Size": float(pre_val), "Post-Size": float(post_val),
                                        "Wear": float(f"{wear_amt:.3f}")
                                    })
                            except:
                                continue
                        if wear_data:
                            st.dataframe(pd.DataFrame(wear_data).sort_values('Borrow Time', ascending=False),
                                         use_container_width=True, hide_index=True)
                        else:
                            st.info("無法解析此區間的歷史尺寸 / Cannot parse history size.")
                    else:
                        st.info("尚無紀錄 / No full log found.")

            # --- 4. 數據統計 ---
            elif admin_menu == t('menu_stats'):
                st.subheader(t('menu_stats'))
                if not df_logs.empty and 'borrow_time' in df_logs.columns:
                    borrow_logs = df_logs[df_logs['borrow_time'] != ""].copy()
                    if not borrow_logs.empty:
                        borrow_logs['date'] = pd.to_datetime(borrow_logs['borrow_time']).dt.date
                        min_date = borrow_logs['date'].min()
                        max_date = borrow_logs['date'].max()
                        col_date1, col_date2 = st.columns(2)
                        with col_date1:
                            start_date = st.date_input(t('stat_start'), min_date, min_value=min_date,
                                                       max_value=max_date)
                        with col_date2:
                            end_date = st.date_input(t('stat_end'), max_date, min_value=min_date, max_value=max_date)

                        mask = (borrow_logs['date'] >= start_date) & (borrow_logs['date'] <= end_date)
                        filtered_logs = borrow_logs[mask]

                        if not filtered_logs.empty:
                            user_counts = filtered_logs['user'].value_counts().reset_index()
                            user_counts.columns = [t('col_user'), 'Count']
                            st.plotly_chart(px.bar(user_counts, x=t('col_user'), y='Count', title=t('stat_user_title'),
                                                   text_auto=True, color='Count', color_continuous_scale='Blues'),
                                            use_container_width=True)

                            item_counts = filtered_logs['gauge_id'].value_counts().reset_index()
                            item_counts.columns = [t('col_id'), 'Count']
                            st.plotly_chart(px.bar(item_counts, x=t('col_id'), y='Count', title=t('stat_item_title'),
                                                   text_auto=True, color='Count', color_continuous_scale='Teal'),
                                            use_container_width=True)
                        else:
                            st.info(t('stat_no_data'))
                    else:
                        st.info(t('stat_no_data'))

            # --- 5. 報廢汰換 ---
            elif admin_menu == t('menu_scrap'):
                st.subheader(t('menu_scrap'))
                active_items = df_g[df_g['status'] != '已報廢']
                if not active_items.empty:
                    scrap_candidates = active_items[active_items['status'] == '需汰換']
                    if not scrap_candidates.empty:
                        st.warning(t('scrap_warn').format(len(scrap_candidates)))
                    opts = active_items.apply(
                        lambda x: f"{x['id']} - {x['category']} ({t('col_status')}: {t('db_' + x['status'])})",
                        axis=1).tolist()
                    sel_item = st.selectbox(t('scrap_sel'), [t('scrap_ph')] + opts)
                    if sel_item != t('scrap_ph'):
                        target_id = sel_item.split(" - ")[0]
                        scrap_note = st.text_input(t('scrap_note'))
                        if st.button(t('scrap_btn'), type="primary"):
                            if scrap_note.strip():
                                update_db(target_id, 'scrap', "Admin", note=scrap_note)
                                st.success(f"✅ {target_id} OK!")
                                st.rerun()
                            else:
                                st.error(t('scrap_err'))
                else:
                    st.info("No items.")

            # --- 6. 事件總紀錄 ---
            elif admin_menu == t('menu_logs'):
                st.subheader(t('menu_logs'))
                st.dataframe(df_logs, use_container_width=True)

            # --- 7. 系統基本設定 ---
            elif admin_menu == t('menu_sys'):
                st.subheader(t('menu_sys'))
                col_sys1, col_sys2 = st.columns(2)
                with col_sys1:
                    st.markdown(t('sys_user_add'))
                    with st.container(border=True):
                        new_user = st.text_input(t('sys_user_name'))
                        if st.button(t('sys_btn_add')):
                            if new_user.strip() and new_user not in user_list:
                                ws_users.append_row([new_user.strip()])
                                get_all_data.clear('users')
                                st.success("✅ OK")
                                st.rerun()
                        st.divider()
                        del_user = st.selectbox(t('sys_user_del'), ["--"] + user_list)
                        if st.button(t('sys_btn_del'), type="primary"):
                            if del_user != "--":
                                try:
                                    row_idx = int(df_users[df_users['name'].astype(str) == str(del_user)].index[0]) + 2
                                    ws_users.delete_rows(row_idx)
                                    get_all_data.clear('users')
                                    st.success("🗑️ OK")
                                    st.rerun()
                                except:
                                    pass

                with col_sys2:
                    st.markdown(t('sys_item_add'))
                    with st.container(border=True):
                        with st.form("add_gauge_form"):
                            new_id = st.text_input(t('sys_item_id'))
                            new_cat = st.text_input(t('sys_item_name'))
                            new_spec = st.text_input(t('sys_item_spec'))
                            if st.form_submit_button(t('sys_btn_item'), type="primary"):
                                if new_id.strip() and new_cat.strip():
                                    if str(new_id) in df_g['id'].astype(str).tolist():
                                        st.error("⚠️ ID exists!")
                                    else:
                                        ws_gauges.append_row(
                                            [new_id.strip(), new_cat.strip(), new_spec.strip(), "可借出", "", "", ""])
                                        get_all_data.clear('gauges')
                                        st.success("✅ OK")
                                        st.rerun()

        else:
            st.warning(t('admin_err_pwd'))


if __name__ == "__main__":
    main()