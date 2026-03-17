import gymnasium as gym
from gymnasium import spaces
import pandas as pd
import numpy as np

class ManagerRouteEnv(gym.Env):
    def __init__(self):
        super(ManagerRouteEnv, self).__init__()
        
        # 1. 데이터 로드
        self.rep_stops = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/01. 12생활권/Result_Representative_Stops_12생활권_KMeans_K=35_평일_[15, 16, 17]시.csv')
        self.flows = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/01. 12생활권/Result_Flows_12생활권_KMeans_K=35_평일_[15, 16, 17]시.csv')
        # self.rep_stops = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/01. 12생활권/Result_Representative_Stops_KMeans_12생활권_평일_[15, 16, 17]시.csv')
        # self.flows = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/01. 12생활권/Result_Flows_KMeans_12생활권_평일_[15, 16, 17]시.csv')
        # self.rep_stops = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/02. 34생활권/Result_Representative_Stops_KMeans_34생활권_평일_[15, 16, 17]시.csv')
        # self.flows = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/01.1. 군집형성 결과/02. 34생활권/Result_Flows_KMeans_34생활권_평일_[15, 16, 17]시.csv')
        
        # self.rep_stops = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/34생활권/Result_Representative_Stops_KMeans_34생활권_평일_[15, 16, 17]시.csv')
        # self.flows = pd.read_csv(r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/34생활권/Result_Flows_KMeans_34생활권_평일_[15, 16, 17]시.csv')

        # [핵심 수정 1] 타입 불일치 원천 차단 (int로 강제 변환)
        self.flows['Start_Cluster'] = self.flows['Start_Cluster'].fillna(-1).astype(int)
        self.flows['End_Cluster'] = self.flows['End_Cluster'].fillna(-1).astype(int)
        
        # 검색 속도 향상을 위해 Dictionary로 변환 (DataFrame 조회는 느림)
        # Key: (Start, End), Value: Volume
        self.flow_lookup = dict(zip(zip(self.flows['Start_Cluster'], self.flows['End_Cluster']), 
                                    self.flows['Volume']))

        # OSRM 데이터 로드 (전처리 단계에서 사용했던 그 파일 경로 입력)
        # 중요: O_ID, D_ID, Total_Dist_Meter 컬럼이 있어야 함
        osrm_path = r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/02. 강화학습 InputData/OSRM_OD_소요시간및거리/OSRM_OD_12생활권 정류장.csv'
        # osrm_path = r'/Users/a82102/Desktop/Python Test/강화학습 가상환경/02. 강화학습 InputData/OSRM_OD_소요시간및거리/OSRM_OD_34생활권 정류장.csv'
        self.df_osrm = pd.read_csv(osrm_path)
        
        # OSRM 검색 속도를 위해 Dictionary로 변환 (Key: (O_ID, D_ID), Value: Dist)
        print(">>> OSRM 데이터 로딩 중 (Lookup Table 생성)...")
        self.dist_lookup = dict(zip(zip(self.df_osrm['O_ID'], self.df_osrm['D_ID']), self.df_osrm['Total_Dist_Meter']))
        print(">>> 로딩 완료!")

        self.cluster_ids = sorted(self.rep_stops['Cluster'].unique())
        self.n_clusters = len(self.cluster_ids)
        
        
        # Action & State
        self.action_space = spaces.Discrete(self.n_clusters)
        # [수정] 좌표 정규화 (MinMax) 및 상태 공간 확장
        self.coords = self.rep_stops[['X', 'Y']].values
        self.coord_min = self.coords.min(axis=0)
        self.coord_max = self.coords.max(axis=0)
        self.norm_coords = (self.coords - self.coord_min) / (self.coord_max - self.coord_min)

        # 관측 공간: [현재위치(One-hot), 방문여부(Binary), 현재X, 현재Y]
        # 기존 shape + 2 (좌표)
        self.observation_space = spaces.Box(low=0, high=1, shape=(self.n_clusters * 2 + 2,), dtype=np.float32)
        
        self.max_stops = 15  # 방문 권역 수
        # __init__ 하단에 추가
        self.rep_stops['Cluster'] = self.rep_stops['Cluster'].astype(int)
        self.cluster_to_id = dict(zip(self.rep_stops['Cluster'], self.rep_stops['ID']))
        


    def reset(self, seed=None, options=None):
        # 1. 상위 클래스 reset 호출 (시드 설정)
        super().reset(seed=seed)
        
        # [수정] 랜덤으로 시작 클러스터 선택
        self.current_cluster = np.random.choice(self.cluster_ids)
        self.current_idx = self.cluster_ids.index(self.current_cluster)
        
        self.visited = np.zeros(self.n_clusters)
        self.visited[self.current_idx] = 1
        
        self.steps = 0
        self.route = [self.current_cluster]
        
        return self._get_state(), {}

    def step(self, action):
        target_cluster = self.cluster_ids[action]
        
        # 1. 제자리 선택 시 (종료 X, 감점 O, 이동 X)
        if target_cluster == self.current_cluster:
            self.steps += 1
            truncated = self.steps >= self.max_stops
            return self._get_state(), -10, False, truncated, {} # 보상 -10

        # 2. 이미 방문한 곳 선택 시 (종료 X, 감점 O, 이동 X)
        if self.visited[action] == 1:
            self.steps += 1
            truncated = self.steps >= self.max_stops
            return self._get_state(), -10, False, truncated, {} # 보상 -10 (종료시키지 않음!)

        # [핵심 수정 2] 보상 계산 시 '왕복 수요' 반영
        # 가는 편(Start->End) + 오는 편(End->Start) 모두 수요로 인정
        fwd_demand = self.flow_lookup.get((self.current_cluster, target_cluster), 0)
        bwd_demand = self.flow_lookup.get((target_cluster, self.current_cluster), 0)
        
        total_segment_demand = fwd_demand + bwd_demand
        
        # 거리 비용 계산
        dist_km = self._get_osrm_dist(self.current_cluster, target_cluster) / 1000.0
        
        # [핵심 수정] 굴곡도(각도) 패널티 계산
        angle_penalty = 0
        if len(self.route) >= 2:
            # 벡터 1: 이전 -> 현재
            prev_idx = self.cluster_ids.index(self.route[-2])
            curr_idx = self.current_idx
            vec1 = self.norm_coords[curr_idx] - self.norm_coords[prev_idx]
            
            # 벡터 2: 현재 -> 다음(Action)
            vec2 = self.norm_coords[action] - self.norm_coords[curr_idx]
            
            # 코사인 유사도 계산 (직진=1, 후진=-1, 90도=0)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 > 0 and norm2 > 0:
                cos_sim = np.dot(vec1, vec2) / (norm1 * norm2)
                # 90도 이상 꺾이면(0보다 작으면) 감점
                if cos_sim < 0.2: 
                    angle_penalty = (1.0 - cos_sim) * 2.0 # 강한 패널티

        # [가중치 수정] 수요 비중 대폭 상향, 거리 비중 유지, 각도 패널티 추가
        # 기존: 수요*3.0, 거리*2.5 -> 음수 발생
        # 수정: 수요*10.0 (적극적 탐색 유도), 거리*2.0, 굴곡도 반영
        # [중요] 보상 비중 조정 제안 (거리 감점을 너무 크게 주지 마세요)
        step_reward = (total_segment_demand * 2.0) - (dist_km * 6.0) # 12생활권 평일 7-8시 용
        # step_reward = (total_segment_demand * 15.0) - (dist_km * 1.0) - angle_penalty # 34생활권 평일 7-8시 용
        # step_reward = (total_segment_demand * 8.0) - (dist_km * 1.0) - angle_penalty # 34생활권 평일 15-17시 용



        self.visited[action] = 1
        self.current_cluster = target_cluster
        self.current_idx = action
        self.route.append(target_cluster)
        self.steps += 1
        
        # 최대 스텝 도달 시에만 종료
        truncated = self.steps >= self.max_stops
        terminated = False # 목표 지점 도착형이 아니므로 False 고정 혹은 특정 조건 시 True

        return self._get_state(), step_reward, terminated, truncated, {}

    def _get_state(self):
        loc_state = np.zeros(self.n_clusters)
        loc_state[self.current_idx] = 1
        
        # [추가] 현재 위치의 정규화된 좌표 가져오기
        cur_xy = self.norm_coords[self.current_idx]
        
        return np.concatenate([loc_state, self.visited, cur_xy])

    def _get_flow_reward(self, start, end):
        row = self.flows[(self.flows['Start_Cluster'] == start) & 
                         (self.flows['End_Cluster'] == end)]
        return row['Volume'].values[0] if not row.empty else 0
    
    def _get_osrm_dist(self, start_cluster, end_cluster):
        # Pandas 조회 대신 딕셔너리(O(1)) 사용으로 즉시 반환
        s_id = self.cluster_to_id.get(start_cluster)
        e_id = self.cluster_to_id.get(end_cluster)
        
        if s_id is None or e_id is None:
            return 50000
            
        return self.dist_lookup.get((s_id, e_id), 50000)