import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# ==============================
# 1. DB 연결 및 초기 설정
# ==============================

@st.cache_resource
def get_connection():
    conn = sqlite3.connect('fridge.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # (1) 식재료 테이블 (컬럼을 CSV 정보에 맞춰 확장했습니다!)
    c.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,          -- 재료명
            category TEXT,      -- 종류
            quantity INTEGER,   -- 수량
            expiry_date DATE,   -- 유통기한 (YYYY-MM-DD)
            storage_tip TEXT,   -- 보관 꿀팁 (Task 5)
            disposal_rule TEXT  -- 분리배출 규칙 (Task 4)
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
    conn.commit()
    
    # ==============================
    # 🌟 CSV 데이터 자동 로드 로직
    # ==============================
    # 1. DB가 비어있는지 확인
    c.execute("SELECT count(*) FROM ingredients")
    count = c.fetchone()[0]
    
    if count == 0:  # 데이터가 하나도 없으면 실행
        csv_file = 'food_data.csv'
        
        if os.path.exists(csv_file):
            try:
                # CSV 읽기
                df = pd.read_csv(csv_file)
                
                # 데이터 가공: '오늘' 날짜 기준으로 유통기한 계산하기
                today = datetime.date.today()
                
                # default_days(권장기간)를 더해서 expiry_date(날짜) 생성
                df['expiry_date'] = df['default_days'].apply(
                    lambda x: today + datetime.timedelta(days=int(x))
                )
                
                # 수량 기본값 1로 설정
                df['quantity'] = 1
                
                # DB 테이블 컬럼 이름과 순서 맞추기
                # (CSV에는 있고 DB에는 없는 컬럼은 제외하고, 필요한 것만 뽑음)
                db_df = df[[
                    'name', 'category', 'quantity', 
                    'expiry_date', 'storage_tip', 'disposal_rule'
                ]]
                
                # DB에 한 번에 저장 (pandas to_sql 기능 활용)
                db_df.to_sql('ingredients', conn, if_exists='append', index=False)
                
                print("✅ food_data.csv 데이터가 성공적으로 로드되었습니다.")
                
            except Exception as e:
                print(f"❌ CSV 로드 중 오류 발생: {e}")
        else:
            print("⚠ food_data.csv 파일이 없습니다. 빈 DB로 시작합니다.")

# 앱 실행 시 초기화 함수 실행
init_db()



# ==============================
# 기본 설정 & 초록(푸릇한) 배경 테마
# ==============================
st.set_page_config(
    page_title="냉장고를 지켜줘",
    page_icon="🥬",
    layout="wide"
)

# 배경 색상 커스텀 (푸릇푸릇)
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
    }
    [data-testid="stSidebar"] {
        background-color: #e8f5e9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🥬 냉장고를 지켜줘 (Save My Fridge)")
st.write("식재료 관리 · 레시피 추천 · 음식물 쓰레기 감소 · 친환경 가이드 서비스")

st.divider()

# ==============================
# 세션 스테이트 초기값
# ==============================
if "ingredients" not in st.session_state:
    st.session_state["ingredients"] = pd.DataFrame(
        {
            "식재료": ["계란", "우유", "상추", "치킨"],
            "종류": ["단백질", "유제품", "채소", "배달음식"],
            "수량": [10, 1, 3, 2],
            "유통기한": [
                datetime.date.today() + datetime.timedelta(days=5),
                datetime.date.today() + datetime.timedelta(days=3),
                datetime.date.today() + datetime.timedelta(days=1),
                datetime.date.today() + datetime.timedelta(days=2),
            ],
        }
    )

if "waste_log" not in st.session_state:
    st.session_state["waste_log"] = pd.DataFrame(
        {
            "날짜": [
                datetime.date.today() - datetime.timedelta(days=21),
                datetime.date.today() - datetime.timedelta(days=14),
                datetime.date.today() - datetime.timedelta(days=7),
                datetime.date.today(),
            ],
            "배출량(g)": [800, 650, 500, 420],
        }
    )

if "point" not in st.session_state:
    st.session_state["point"] = 40  # 대충 시작 포인트

# ==============================
# 사이드바 메뉴
# ==============================
menu = st.sidebar.radio(
    "메뉴 선택",
    [
        "홈",
        "식재료 관리",
        "소비기한 알림",
        "레시피 추천",
        "음식물 쓰레기 분석",
        "환경/분리배출 가이드",
        "마이페이지(포인트)",
    ],
)

# ==============================
# 0. 홈
# ==============================
if menu == "홈":
    st.header("📌 서비스 개요")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("프로젝트 컨셉")
        st.write(
            """
            - 냉장고 속 식재료를 **등록**하고  
            - 임박한 식재료를 **알림**받고  
            - 그 재료를 활용한 **레시피**를 추천받고  
            - 결과적으로 **음식물 쓰레기를 줄이는** 서비스입니다.
            """
        )

        st.success("왼쪽 메뉴에서 기능을 선택해 사용할 수 있습니다.")

    with col2:
        st.subheader("요약 지표 (샘플)")
        a, b = st.columns(2)
        c, d = st.columns(2)

        a.metric("이번 주 음식물 쓰레기", "420 g", "-80 g")
        b.metric("임박 식재료 수", "2 개", "+1")
        c.metric("총 등록 식재료", f"{len(st.session_state['ingredients'])} 개")
        d.metric("현재 포인트", f"{st.session_state['point']} P")

# ==============================
# 1. 식재료 관리
# (Task1 + Task6 컬럼 레이아웃 활용)
# ==============================
elif menu == "식재료 관리":
    st.header("🥕 식재료 등록 / 관리")

    left, right = st.columns(2)

    with left:
        st.subheader("새 식재료 등록")

        name = st.text_input("식재료명")
        kind = st.selectbox("종류", ["채소", "과일", "단백질", "유제품", "배달음식", "기타"])
        qty = st.number_input("수량", min_value=1, step=1, value=1)
        expire = st.date_input("유통기한", value=datetime.date.today())

        if st.button("등록하기"):
            if name.strip() == "":
                st.warning("식재료명을 입력해 주세요.")
            else:
                new_row = pd.DataFrame(
                    {
                        "식재료": [name],
                        "종류": [kind],
                        "수량": [qty],
                        "유통기한": [expire],
                    }
                )
                st.session_state["ingredients"] = pd.concat(
                    [st.session_state["ingredients"], new_row],
                    ignore_index=True,
                )
                st.success(f"{name} 이(가) 등록되었습니다!")

    with right:
        st.subheader("현재 등록된 식재료")
        st.dataframe(st.session_state["ingredients"])

# ==============================
# 2. 소비기한 알림
# (Task2 metric + 남은 일수 계산)
# ==============================
elif menu == "소비기한 알림":
    st.header("⏰ 소비기한 알림")

    df = st.session_state["ingredients"].copy()

    # 남은 일수 계산 (dt 안 쓰는 안전한 방식)
    def calc_days_left(d):
        if isinstance(d, (datetime.date, datetime.datetime, pd.Timestamp)):
            return (d - datetime.date.today()).days
        return None

    df["남은 일수"] = df["유통기한"].apply(calc_days_left)
    df = df.sort_values("남은 일수")

    st.subheader("📋 식재료 소비기한 목록")
    st.dataframe(df)

    st.subheader("📊 임박 식재료 지표 (상위 4개)")

    top = df.head(4).reset_index(drop=True)
    cols = st.columns(len(top))

    for i, row in top.iterrows():
        delta_text = f"{row['남은 일수']}일 남음"
        cols[i].metric(
            row["식재료"],
            delta_text,
            None,
            border=True,
        )

    st.info("※ 남은 일수가 0 이하인 경우, 이미 소비기한이 지난 식재료입니다.")

# ==============================
# 3. 레시피 추천
# (Task4 형태의 필터 + 바 차트)
# ==============================
elif menu == "레시피 추천":
    st.header("🍳 레시피 추천") 

    st.write("보유 중인 식재료를 선택하면 추천 레시피를 보여줍니다. (샘플 데이터)")

    recipes = pd.DataFrame(
        {
            "레시피": ["계란후라이", "치킨마요덮밥", "상추샐러드", "우유푸딩"],
            "필요재료": ["계란", "치킨,마요네즈", "상추,채소", "우유,설탕"],
            "유형": ["간단요리", "배달음식재활용", "샐러드", "디저트"],
            "칼로리(kcal)": [180, 700, 150, 250],
        }
    )

    ingredients_list = sorted(st.session_state["ingredients"]["식재료"].unique().tolist())
    selected_ing = st.multiselect("보유 재료 선택", ingredients_list, default=ingredients_list[:1])

    filtered = recipes.copy()
    if selected_ing:
        # 선택한 재료가 하나라도 포함된 레시피 필터링
        mask = filtered["필요재료"].apply(
            lambda s: any(ing in s for ing in selected_ing)
        )
        filtered = filtered[mask]

    type_filter = st.selectbox("레시피 유형 필터", ["전체"] + sorted(recipes["유형"].unique().tolist()))
    if type_filter != "전체":
        filtered = filtered[filtered["유형"] == type_filter]

    st.subheader("추천 레시피 목록")
    st.dataframe(filtered)

    if not filtered.empty:
        st.subheader("칼로리 비교")
        st.bar_chart(filtered.set_index("레시피")["칼로리(kcal)"])
    else:
        st.warning("선택한 재료로 만들 수 있는 레시피가 없습니다. 재료를 더 선택해 보세요.")

# ==============================
# 4. 음식물 쓰레기 분석
# (Task4 차트 형태 응용)
# ==============================
elif menu == "음식물 쓰레기 분석":
    st.header("🗑 음식물 쓰레기 배출량 분석")

    waste_df = st.session_state["waste_log"].copy()
    waste_df = waste_df.sort_values("날짜")

    st.subheader("기록된 배출량")
    st.dataframe(waste_df)

    st.subheader("시간에 따른 배출량 변화")
    chart_df = waste_df.set_index("날짜")
    st.line_chart(chart_df["배출량(g)"])

    # 감소량 계산
    if len(waste_df) >= 2:
        diff = waste_df["배출량(g)"].iloc[0] - waste_df["배출량(g)"].iloc[-1]
        if diff > 0:
            st.success(f"📉 처음 기록 대비 음식물 쓰레기가 {diff} g 줄었습니다! 멋져요 💚")
        elif diff == 0:
            st.info("배출량 변화가 없습니다.")
        else:
            st.warning(f"⚠ 음식물 쓰레기가 {abs(diff)} g 늘어났습니다. 다시 한 번 냉장고를 점검해볼까요?")

    st.divider()
    st.subheader("새 배출량 기록 추가")

    col1, col2 = st.columns(2)
    with col1:
        new_date = st.date_input("날짜 선택", value=datetime.date.today())
    with col2:
        new_amount = st.number_input("배출량(g)", min_value=0, step=10, value=300)

    if st.button("기록 추가"):
        new_row = pd.DataFrame({"날짜": [new_date], "배출량(g)": [new_amount]})
        st.session_state["waste_log"] = pd.concat(
            [st.session_state["waste_log"], new_row],
            ignore_index=True,
        )
        st.success("새로운 배출량 기록이 추가되었습니다.")

# ==============================
# 5. 환경/분리배출 가이드
# (Task6 Tabs + Expander 응용)
# ==============================
elif menu == "환경/분리배출 가이드":
    st.header("♻ 환경 / 분리배출 가이드")

    tab1, tab2, tab3 = st.tabs(["음식물", "플라스틱/배달용기", "기타 팁"])

    with tab1:
        st.subheader("음식물 쓰레기 분리배출")
        with st.expander("음식물로 버려도 되는 것"):
            st.write("- 채소 껍질 (일부), 과일 껍질, 밥/국 등 일반 음식물")
        with st.expander("음식물로 버리면 안 되는 것"):
            st.write("- 큰 뼈, 조개껍질, 티백, 한약재, 호두껍질 등")

    with tab2:
        st.subheader("플라스틱/배달용기 처리")
        with st.expander("플라스틱 용기"):
            st.write("- 내용물 비우기 → 물로 헹구기 → 플라스틱으로 배출")
        with st.expander("일회용 컵/뚜껑/빨대"):
            st.write("- 컵: 플라스틱 / 빨대 & 코팅 종이컵: 일반 쓰레기")
        with st.expander("배달 음식 비닐/포장재"):
            st.write("- 음식물 완전히 제거 후 재질에 맞게 분리배출")

    with tab3:
        st.subheader("냉장고/식재료 관리 팁")
        st.write("- 주 1회 냉장고 정리하기")
        st.write("- 유통기한이 임박한 식재료부터 사용하기 (앱의 알림 기능 활용)")
        st.write("- 같은 재료를 너무 많이 사지 않도록 장보기 전 재고 확인")

# ==============================
# 6. 마이페이지 (포인트 시스템)
# (Task7 세션 + Progress bar 응용)
# ==============================
elif menu == "마이페이지(포인트)":
    st.header("⭐ 마이페이지 / 포인트 제도")

    st.subheader(f"현재 포인트: {st.session_state['point']} P")

    st.write("친환경 행동을 할수록 포인트가 올라갑니다.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("임박 재료 사용 (+30P)"):
            st.session_state["point"] += 30
            st.success("임박 재료를 잘 사용했어요! +30P")

    with col2:
        if st.button("배달음식 재활용 레시피 실천 (+20P)"):
            st.session_state["point"] += 20
            st.success("배달음식을 버리지 않고 재활용했어요! +20P")

    with col3:
        if st.button("음식물 쓰레기 저번 주보다 감소 (+40P)"):
            st.session_state["point"] += 40
            st.success("음식물 쓰레기를 줄였어요! +40P")

    st.divider()

    # 100점 기준 레벨 바
    level = st.session_state["point"] // 100 + 1
    progress_in_level = st.session_state["point"] % 100

    st.subheader(f"현재 레벨: Lv.{level}")
    st.progress(progress_in_level / 100.0)
    st.write(f"다음 레벨까지 {100 - progress_in_level} P 남았습니다.")
