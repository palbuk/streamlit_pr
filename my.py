import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# ==========================================
# 1. DB 연결 및 초기화 (핵심 로직)
# ==========================================

@st.cache_resource
def get_connection():
    # check_same_thread=False는 스트림릿에서 필수
    conn = sqlite3.connect('fridge.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # (1) 식재료 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,          -- 재료명
            category TEXT,      -- 종류
            quantity INTEGER,   -- 수량
            expiry_date DATE,   -- 유통기한
            storage_tip TEXT,   -- 보관 꿀팁
            disposal_rule TEXT  -- 분리배출 규칙
        )
    ''')

    # (2) 음식물 쓰레기 로그 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_date DATE,
            amount_g INTEGER
        )
    ''')

    # (3) 포인트 로그 테이블 (새로 추가됨)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            points INTEGER
        )
    ''')
    
    conn.commit()
    
    # ------------------------------------------
    # 🌟 CSV 데이터 자동 로드 (DB가 비었을 때만)
    # ------------------------------------------
    c.execute("SELECT count(*) FROM ingredients")
    count = c.fetchone()[0]
    
    if count == 0:
        csv_file = 'food_data.csv'
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                
                # 유통기한 계산 (오늘 + 권장일수)
                today = datetime.date.today()
                df['expiry_date'] = df['default_days'].apply(
                    lambda x: today + datetime.timedelta(days=int(x))
                )
                df['quantity'] = 1 # 기본 수량
                
                # DB 컬럼에 맞춰서 데이터프레임 정리
                # (CSV에 없는 컬럼이 있으면 에러나므로 필요한 것만 선택)
                db_df = df[['name', 'category', 'quantity', 'expiry_date', 'storage_tip', 'disposal_rule']]
                
                # DB 저장
                db_df.to_sql('ingredients', conn, if_exists='append', index=False)
                print("✅ CSV 데이터 로드 완료")
                
            except Exception as e:
                print(f"❌ CSV 로드 오류: {e}")

# 앱 시작 시 DB 초기화 실행
init_db()

# ==========================================
# 2. DB 헬퍼 함수들 (SQL 쿼리 모음)
# ==========================================
def run_query(query, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()

def get_data(query, params=()):
    conn = get_connection()
    return pd.read_sql(query, conn, params=params)

# ==========================================
# 3. UI 기본 설정
# ==========================================
st.set_page_config(page_title="냉장고를 지켜줘", page_icon="🥬", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #e8f5e9, #f1f8e9); }
    [data-testid="stSidebar"] { background-color: #e8f5e9; }
    </style>
    """, unsafe_allow_html=True)

st.title("🥬 냉장고를 지켜줘 (Save My Fridge)")
st.write("식재료 관리 · 레시피 추천 · 음식물 쓰레기 감소 · 친환경 가이드 서비스")
st.divider()

# ==========================================
# 4. 사이드바 및 페이지 라우팅
# ==========================================
menu = st.sidebar.radio("메뉴 선택", [
    "홈", "식재료 관리", "소비기한 알림", "레시피 추천", 
    "음식물 쓰레기 분석", "환경/분리배출 가이드", "마이페이지(포인트)"
])

# ------------------------------------------
# (0) 홈
# ------------------------------------------
if menu == "홈":
    st.header("📌 서비스 개요")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("프로젝트 컨셉")
        st.info("""
        - **식재료 관리**: 냉장고 속 재료를 한눈에 파악하고 관리합니다.
        - **소비기한 알림**: 유통기한 임박 재료를 알려주어 낭비를 막습니다.
        - **레시피 추천**: 남은 재료를 활용할 수 있는 요리를 추천합니다.
        - **환경 보호**: 음식물 쓰레기를 줄이고 분리배출 꿀팁을 제공합니다.
        """)
        
    with col2:
        st.subheader("현재 상태 요약")
        
        # DB에서 실시간 데이터 조회
        ing_count = get_data("SELECT count(*) as cnt FROM ingredients").iloc[0]['cnt']
        waste_sum = get_data("SELECT sum(amount_g) as s FROM waste_log").iloc[0]['s']
        point_sum = get_data("SELECT sum(points) as p FROM user_points").iloc[0]['p']
        
        # 값이 없으면 0으로 처리
        waste_sum = waste_sum if waste_sum else 0
        point_sum = point_sum if point_sum else 0

        a, b = st.columns(2)
        a.metric("총 등록 식재료", f"{ing_count} 개")
        b.metric("현재 내 포인트", f"{point_sum} P")

# ------------------------------------------
# (1) 식재료 관리 (DB 연동)
# ------------------------------------------
elif menu == "식재료 관리":
    st.header("🥕 식재료 등록 / 관리")
    
    left, right = st.columns([1, 2])
    
    with left:
        st.subheader("새 식재료 등록")
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("식재료명")
            kind = st.selectbox("종류", ["채소", "과일", "단백질", "유제품", "배달음식", "기타"])
            qty = st.number_input("수량", 1, 100, 1)
            expire = st.date_input("유통기한")
            
            # 추가 정보 (선택사항)
            tip = st.text_input("보관 꿀팁 (선택)")
            rule = st.text_input("분리배출 규칙 (선택)")
            
            submitted = st.form_submit_button("DB에 저장하기")
            
            if submitted:
                if name:
                    run_query(
                        "INSERT INTO ingredients (name, category, quantity, expiry_date, storage_tip, disposal_rule) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, kind, qty, expire, tip, rule)
                    )
                    st.success(f"✅ {name} 저장 완료!")
                    st.rerun() # 새로고침해서 목록 갱신
                else:
                    st.warning("이름을 입력해주세요.")

    with right:
        st.subheader("📦 냉장고 목록 (DB 조회)")
        
        # DB에서 불러오기
        df = get_data("SELECT * FROM ingredients ORDER BY expiry_date")
        
        # 데이터프레임 보여주기 (삭제 기능 포함)
        if not df.empty:
            st.dataframe(
                df, 
                column_config={
                    "id": "ID",
                    "name": "재료명",
                    "expiry_date": "유통기한",
                    "storage_tip": "💡 보관팁",
                    "disposal_rule": "♻ 분리배출"
                },
                hide_index=True,
                use_container_width=True
            )
            
            # 삭제 기능
            with st.expander("🗑 식재료 삭제하기"):
                del_id = st.selectbox("삭제할 재료 선택 (ID - 이름)", 
                                      df.apply(lambda x: f"{x['id']} - {x['name']}", axis=1))
                if st.button("선택한 재료 삭제"):
                    real_id = del_id.split(" - ")[0]
                    run_query("DELETE FROM ingredients WHERE id = ?", (real_id,))
                    st.success("삭제되었습니다.")
                    st.rerun()
        else:
            st.info("냉장고가 비어있습니다. 왼쪽에서 재료를 추가해주세요.")

# ------------------------------------------
# (2) 소비기한 알림 (DB 연동 + 액션 추가)
# ------------------------------------------
elif menu == "소비기한 알림":
    st.header("⏰ 소비기한 알림")
    
    # DB에서 데이터 가져오기
    df = get_data("SELECT * FROM ingredients")
    
    if df.empty:
        st.warning("데이터가 없습니다.")
    else:
        # 날짜 계산을 위해 datetime 변환
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        df['남은일수'] = df['expiry_date'].apply(lambda x: (x - datetime.date.today()).days)
        
        # 정렬
        df = df.sort_values('남은일수')
        
        st.subheader("🚨 유통기한 임박 재료")
        
        # 카드 형태로 보여주기 (상위 3개)
        top_items = df.head(3)
        cols = st.columns(3)
        
        for idx, row in enumerate(top_items.iterrows()):
            data = row[1] # row 데이터
            col_idx = idx % 3
            
            with cols[col_idx]:
                st.info(f"**{data['name']}**")
                days = data['남은일수']
                
                if days < 0:
                    st.error(f"😱 {abs(days)}일 지남!")
                elif days <= 3:
                    st.warning(f"⚠ {days}일 남음")
                else:
                    st.success(f"{days}일 남음")
                
                # 액션 버튼 (사용함 / 버림)
                c1, c2 = st.columns(2)
                if c1.button("😋 먹음", key=f"eat_{data['id']}"):
                    # 1. 포인트 추가
                    run_query("INSERT INTO user_points (description, points) VALUES (?, ?)", (f"{data['name']} 알뜰 사용", 30))
                    # 2. 재료 삭제
                    run_query("DELETE FROM ingredients WHERE id = ?", (data['id'],))
                    st.toast(f"{data['name']} 사용 완료! +30P")
                    st.rerun()
                    
                if c2.button("🗑 버림", key=f"trash_{data['id']}"):
                    # 1. 쓰레기 기록
                    run_query("INSERT INTO waste_log (waste_date, amount_g) VALUES (?, ?)", (datetime.date.today(), 300)) # 대충 300g
                    # 2. 재료 삭제
                    run_query("DELETE FROM ingredients WHERE id = ?", (data['id'],))
                    st.toast(f"{data['name']} 버림 처리됨..")
                    st.rerun()

        st.divider()
        st.subheader("전체 목록")
        st.dataframe(df[['name', 'expiry_date', '남은일수', 'storage_tip']])

# ------------------------------------------
# (3) 레시피 추천 (DB 식재료 연동)
# ------------------------------------------
elif menu == "레시피 추천":
    st.header("🍳 레시피 추천")
    
    # DB에 있는 재료 목록 가져오기
    ing_df = get_data("SELECT DISTINCT name FROM ingredients")
    my_ingredients = ing_df['name'].tolist()
    
    # 레시피 데이터 (이건 DB보다 하드코딩이 보여주기 편해서 유지)
    recipes = pd.DataFrame({
        "레시피": ["계란후라이", "치킨마요덮밥", "상추샐러드", "두부김치", "제육볶음"],
        "필요재료": ["계란", "치킨,마요네즈", "상추,채소", "두부,김치", "돼지고기,양파"],
        "유형": ["간단요리", "배달음식재활용", "다이어트", "한식", "메인요리"],
        "칼로리": [120, 700, 80, 400, 600]
    })
    
    if not my_ingredients:
        st.warning("냉장고에 재료가 없어요! 먼저 재료를 등록해주세요.")
    else:
        selected = st.multiselect("냉장고 속 재료 선택", my_ingredients)
        
        if selected:
            # 선택한 재료가 포함된 레시피 필터링
            mask = recipes["필요재료"].apply(lambda x: any(ing in x for ing in selected))
            result = recipes[mask]
            
            st.write(f"🔍 **{', '.join(selected)}** (으)로 만들 수 있는 요리:")
            st.dataframe(result, use_container_width=True)
            
            if not result.empty:
                st.bar_chart(result.set_index("레시피")["칼로리"])
        else:
            st.info("재료를 선택하면 레시피가 나옵니다.")

# ------------------------------------------
# (4) 음식물 쓰레기 분석 (DB 연동)
# ------------------------------------------
elif menu == "음식물 쓰레기 분석":
    st.header("🗑 음식물 쓰레기 로그")
    
    # DB 기록 불러오기
    log_df = get_data("SELECT * FROM waste_log ORDER BY waste_date")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if not log_df.empty:
            st.line_chart(log_df.set_index("waste_date")["amount_g"])
            
            # 분석 멘트
            total = log_df['amount_g'].sum()
            st.write(f"📝 지금까지 총 배출량: **{total} g**")
        else:
            st.info("아직 버려진 음식물 기록이 없습니다. (좋은 소식이네요!)")
            
    with col2:
        st.subheader("기록 추가")
        d = st.date_input("날짜", datetime.date.today())
        amt = st.number_input("배출량(g)", 100, 2000, 300)
        
        if st.button("기록 저장"):
            run_query("INSERT INTO waste_log (waste_date, amount_g) VALUES (?, ?)", (d, amt))
            st.success("저장되었습니다.")
            st.rerun()

# ------------------------------------------
# (5) 환경/분리배출 가이드 (DB 검색 기능 추가)
# ------------------------------------------
elif menu == "환경/분리배출 가이드":
    st.header("♻ 환경 가이드 & 검색")
    
    st.info("💡 CSV에서 불러온 데이터를 여기서 검색할 수 있습니다.")
    
    search_term = st.text_input("재료 이름 검색 (예: 계란, 치킨)")
    
    if search_term:
        # DB에서 검색 (LIKE 문법 사용)
        res = get_data(f"SELECT name, disposal_rule, storage_tip FROM ingredients WHERE name LIKE '%{search_term}%'")
        if not res.empty:
            for idx, row in res.iterrows():
                with st.expander(f"📌 {row['name']} 정보 보기", expanded=True):
                    st.write(f"**🗑 분리배출:** {row['disposal_rule']}")
                    st.write(f"**❄️ 보관꿀팁:** {row['storage_tip']}")
        else:
            st.warning("등록된 정보가 없습니다. (CSV에 없는 재료일 수 있습니다)")
            
    st.divider()
    # 기존 탭 유지
    t1, t2 = st.tabs(["일반 상식", "플라스틱 가이드"])
    with t1:
        st.write("- **음식물 쓰레기**: 동물 사료로 쓸 수 있는 것 (부드러운 것)")
        st.write("- **일반 쓰레기**: 뼈, 껍데기, 씨앗, 티백 등")
    with t2:
        st.write("- 내용은 비우고, 라벨은 떼고, 찌그러트려서 배출!")

# ------------------------------------------
# (6) 마이페이지 (DB 포인트 연동) - 수정됨
# ------------------------------------------
elif menu == "마이페이지(포인트)":
    st.header("⭐ 나의 에코 포인트")
    
    # 총 포인트 계산
    point_df = get_data("SELECT * FROM user_points ORDER BY action_date DESC")
    total_point = point_df['points'].sum() if not point_df.empty else 0
    
    # 레벨 계산 (0점으로 시작하므로 0~99점은 Lv.1)
    level = total_point // 100 + 1
    remain = 100 - (total_point % 100)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("현재 총 포인트", f"{total_point} P")
        st.metric("내 레벨", f"Lv. {level}")
        st.write(f"다음 레벨까지 **{remain} P** 남음")
        st.progress((total_point % 100) / 100)
        
    with col2:
        st.subheader("📝 포인트 적립 내역")
        if not point_df.empty:
            st.dataframe(
                point_df[['action_date', 'description', 'points']], 
                hide_index=True,  # 인덱스(0,1,2) 숨기기
                use_container_width=True,
                column_config={
                    "action_date": "날짜/시간",
                    "description": "내역",
                    "points": "포인트"
                }
            )
        else:
            st.info("아직 활동 내역이 없습니다.")
            
    # ▼ [수정됨] 버튼 이름과 기능 변경
    if st.button("출석체크 (+10P)"):
        # 하루에 한 번만 가능한 로직을 넣을 수도 있지만, 일단 기능 구현 위주로
        run_query("INSERT INTO user_points (description, points) VALUES (?, ?)", ("출석체크", 10))
        st.toast("출석체크 완료! 10포인트가 적립되었습니다.") # 알림 메시지도 예쁘게
        st.rerun()