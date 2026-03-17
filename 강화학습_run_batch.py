import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from env import ManagerRouteEnv
import os
import time
import contextily as cx
from datetime import datetime
import matplotlib.pyplot as plt

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
N_TOTAL_RUNS = 500          # 총 반복 횟수
TIMESTEPS_PER_RUN = 100000  # 회차당 학습 횟수
OUTPUT_FILE = "Batch_Training_Results_12생활권_K=35_평일_15-17시.csv" # 엑셀 저장 파일명
IMAGE_DIR = "Batch_Images_12생활권_K=35_평일_15-17시"  # 이미지가 저장될 폴더명
# OUTPUT_FILE = "Batch_Training_Results_34생활권_평일_15-17시.csv" # 엑셀 저장 파일명
# IMAGE_DIR = "Batch_Images_34생활권_평일_15-17시"  # 이미지가 저장될 폴더명


# 계산 상수
DAYS_IN_MONTH = 20          # 5월 평일 수 (나눗셈용)
MIN_PER_KM = 3.4            # km당 소요시간 (분)
REST_TIME_MIN = 5          # 기사 휴게시간 (분)

# ==========================================
# 2. 시각화 함수 (수정됨)
# ==========================================
def save_route_image(rep_stops, route_clusters, run_id, save_dir):
    # ax 객체 제어를 위해 subplots 사용
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # 배경: 전체 권역
    ax.scatter(rep_stops['X'], rep_stops['Y'], c='lightgray', s=100, label='Clusters')
    for _, row in rep_stops.iterrows():
        ax.text(row['X'], row['Y'], str(int(row['Cluster'])), fontsize=13, color='black')

    # 경로 그리기
    route_x, route_y = [], []
    for cluster_id in route_clusters:
        row = rep_stops[rep_stops['Cluster'] == cluster_id]
        if not row.empty:
            route_x.append(row.iloc[0]['X'])
            route_y.append(row.iloc[0]['Y'])
            
    ax.plot(route_x, route_y, c='blue', linewidth=1, linestyle='--', alpha=0.7, label='Learned Route')
    
    for i in range(len(route_x) - 1):
        ax.arrow(route_x[i], route_y[i], route_x[i+1]-route_x[i], route_y[i+1]-route_y[i],
                  head_width=0.0003, color='blue', length_includes_head=True)
        ax.text(route_x[i], route_y[i], str(i+1), fontsize=12, fontweight='bold', color='red', zorder=5)
    
    formatted_title = " -> ".join(map(str, route_clusters))
    ax.set_title(f"[Run {run_id}] Route: {formatted_title}", fontsize=15)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # [추가됨] OpenStreetMap 배경 추가
    # 좌표계가 위경도(Longitude/Latitude)라고 가정하고 crs='EPSG:4326' 설정
    try:
        cx.add_basemap(ax, crs='EPSG:4326', source=cx.providers.OpenStreetMap.Mapnik)
    except Exception as e:
        print(f"Warning: 지도 배경을 불러오지 못했습니다. ({e})")
    
    file_path = os.path.join(save_dir, f"Run_{run_id:03d}.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    return file_path

# ==========================================
# 3. 메인 루프 (계산 로직 추가됨)
# ==========================================
def run_batch_simulation():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    all_results = []
    print(f"[{datetime.now()}] >>> 야간 자동화 학습 시작 (총 {N_TOTAL_RUNS}회)")

    start_time_total = time.time()

    for i in range(1, N_TOTAL_RUNS + 1):
        run_start_time = time.time()
        print(f"--- [Run {i:03d}/{N_TOTAL_RUNS}] 학습 진행 중... ---")
        
        # 1. 환경/모델 초기화 및 학습
        env = ManagerRouteEnv()
        model = PPO("MlpPolicy", env, verbose=0, learning_rate=0.0003, ent_coef=0.01, gamma=0.99)
        model.learn(total_timesteps=TIMESTEPS_PER_RUN)
        
        # 2. 결과 경로 추출 및 Reward 합산 [수정됨]
        obs, _ = env.reset()
        done = False
        truncated = False
        total_episode_reward = 0.0
        
        # [수정] 무한 루프 방지용 카운터 추가
        safety_step_count = 0
        MAX_SAFETY_STEPS = 50  # 최대 허용 스텝 수
        
        while not done and not truncated:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, _ = env.step(action)
            total_episode_reward += reward
            
            # [수정] 강제 종료 로직
            safety_step_count += 1
            if safety_step_count > MAX_SAFETY_STEPS:
                print(f"  >>> 경고: 무한 루프 감지되어 강제 종료합니다. (Step: {safety_step_count})")
                break
        
        print(f"생성된 노선: {env.route}")

        route_clusters = env.route
        
        
        
        # ==========================================
        # [NEW] 상세 지표 계산 (왕복 + 경유 수요 포함)
        # ==========================================
        total_dist_meter = 0
        total_demand_monthly = 0
        
        # 1. 총 운행 거리 계산 (인접 구간 합산) - OSRM 기준
        for idx in range(len(route_clusters) - 1):
            s_id = env.rep_stops[env.rep_stops['Cluster'] == route_clusters[idx]].iloc[0]['ID']
            e_id = env.rep_stops[env.rep_stops['Cluster'] == route_clusters[idx+1]].iloc[0]['ID']
            dist = env.dist_lookup.get((s_id, e_id), 0)
            total_dist_meter += dist

        # 2. 총 이용 수요 계산 (왕복 & 경유 포함 모든 조합) - Flow 기준
        # 노선이 1 -> 2 -> 3 일 때:
        # 커버하는 수요: (1->2), (1->3), (2->3) AND (3->2), (3->1), (2->1)
        
        # route_clusters 리스트에 있는 모든 노드 조합 확인
        unique_nodes_in_route = list(set(route_clusters)) # 중복 제거 (혹시 모를 순환 대비)
        
        # 이중 루프로 모든 가능한 쌍(Pair) 검사
        for start_node in unique_nodes_in_route:
            for end_node in unique_nodes_in_route:
                if start_node == end_node:
                    continue
                
                # 해당 OD(start->end)의 수요가 Flow 데이터에 있는지 확인
                # env.py에서 만든 flow_lookup을 쓰거나 dataframe 조회
                # (Batch 파일에서는 env 객체를 새로 만들었으므로 env.flow_lookup 사용 가능)
                
                # 주의: env.flow_lookup은 env.__init__에서 생성됨. 
                # run_batch.py에서도 env = ManagerRouteEnv() 했으므로 접근 가능.
                demand = env.flow_lookup.get((start_node, end_node), 0)
                
                # 경로상에 Start와 End가 모두 존재하면 해당 수요를 흡수한 것으로 간주
                # (단순 존재 여부만 체크해도 됨. 왜냐하면 왕복 노선이므로 순서는 상관없음)
                if demand > 0:
                    total_demand_monthly += demand

        # 3. 최종 지표 환산
        total_dist_km = total_dist_meter / 1000.0
        # 편도 운행 거리 * 2 (왕복 가정 시 거리도 2배, 시간도 2배 해야 함? 
        # -> 보통 '노선 길이'는 편도 기준, '배차'는 왕복 기준.
        # -> 여기서는 사용자가 "순환형이 아닌 일직선"이라 했으므로,
        #    지금 구한 total_dist_meter는 '편도' 거리임.
        #    따라서 왕복 운행시간 = 편도거리 * 2 * 3.4분 ?
        #    질문에서 "운행시간은 km당 3.4분"이라고만 했으므로 편도 기준인지 왕복 기준인지 정의 필요.
        #    [가정] 배차간격을 논하려면 '1회 왕복 운행시간'이 필요함. 따라서 거리에 2배를 곱해 시간 계산.
        
        round_trip_dist_km = total_dist_km * 2
        driving_time_min = round_trip_dist_km * MIN_PER_KM
        total_cycle_time_min = driving_time_min + REST_TIME_MIN # 휴게시간 포함
        
        # daily_avg_demand = total_demand_monthly / DAYS_IN_MONTH
        
        # 운행 시간 및 배차 관련
        driving_time_min = total_dist_km * MIN_PER_KM
        total_cycle_time_min = driving_time_min + REST_TIME_MIN

        # ==========================================
        # 데이터 포맷팅 및 저장
        # ==========================================
        formatted_route_str = " -> ".join([str(int(c)) for c in route_clusters])
        
        route_stop_ids = []
        route_stop_names = []
        for c_id in route_clusters:
            row = env.rep_stops[env.rep_stops['Cluster'] == c_id]
            if not row.empty:
                route_stop_ids.append(str(row.iloc[0]['ID']))
                route_stop_names.append(row.iloc[0]['Name'])
            else:
                route_stop_ids.append("Unknown")

        image_path = save_route_image(env.rep_stops, route_clusters, i, IMAGE_DIR)

        result_data = {
            '회차': i,
            # [NEW] AI가 판단한 보상 점수 추가
            'RL_Reward_Score': round(total_episode_reward, 2),
            # '일평균_이용수요(명)': round(daily_avg_demand, 1),
            '총_운행거리(km)': round(total_dist_km, 2),
            '순수_운행시간(분)': round(driving_time_min, 1),
            '1회_순환_시간(휴게10분포함)': round(total_cycle_time_min, 1),
            '월_일평균 이용수요(명/일)': int(total_demand_monthly),
            # -----------------
            '생성된_권역_경로': formatted_route_str,
            '경로_정류장명': " -> ".join(route_stop_names),
            '경로_정류장ID': " -> ".join(route_stop_ids),
            '이미지_파일': image_path,
            '생성시각': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        all_results.append(result_data)
        
        # 엑셀 저장
        df_results = pd.DataFrame(all_results)
        try:
            df_results.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            print(f">>> [Run {i:03d}] 저장 완료 (이용수요: {int(total_demand_monthly)}(명/일) / 운행시간: {int(total_cycle_time_min)}(분) / 점수: {round(total_episode_reward, 2)}")
        except Exception as e:
            print(f"!!! 저장 실패: {e}")

    total_duration = time.time() - start_time_total
    print(f"\n[{datetime.now()}] >>> 모든 학습 종료! (총 소요시간: {total_duration/3600:.2f}시간)")

if __name__ == "__main__":
    run_batch_simulation()