from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Case, When, Value, CharField, F # F 추가
from .models import DrivingHistory

@api_view(['POST'])
def DrivingHistoryList(request):
    data = request.data
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    dispatch_types = data.get('dispatch_types', [])
    booking_methods = data.get('booking_methods', [])
    
    # [추가] PySide6에서 넘어온 라디오 버튼 값
    day_type = data.get('day_type', 'All') 

    if not start_date or not end_date:
        return Response({"error": "날짜 조건이 누락되었습니다."}, status=400)

    filters = {'날짜__solar_date__range': [start_date, end_date]} 
    
    if dispatch_types:
        filters['배차분류__in'] = dispatch_types
    if booking_methods:
        filters['호출방법__in'] = booking_methods

    # [핵심] 평일/휴일 필터링 적용 (DB의 실제 휴일 플래그가 'Y'라고 가정)
    if day_type == 'Holiday':
        filters['날짜__is_holiday'] = 'Y'
    elif day_type == 'Weekday':
        # 휴일이 아닌 것 (N, NULL, 빈 문자열 등)
        filters['날짜__is_holiday__in'] = ['N', '', None] 

    # 1. 필터링 수행
    queryset = DrivingHistory.objects.select_related('날짜').filter(**filters)
    
    # 2. 조건문(Case/When) 및 합산 로직(F) 추가
    queryset = queryset.annotate(
        day_type_label=Case(
            When(날짜__is_holiday='Y', then=Value('휴일')),
            default=Value('평일'),
            output_field=CharField()
        ),
        # [핵심] 여기서 3개 필드를 더해 '이용인원'이라는 가상 컬럼 생성
        이용인원=F('성인') + F('청소년') + F('어린이') 
    )
    
    # 3. 데이터 추출 (가져올 필드에 '이용인원' 추가)
    all_fields = [f.name for f in DrivingHistory._meta.fields]
    
    raw_data = list(queryset.values(*all_fields, 'day_type_label', '이용인원'))
    
    # 4. [수정] 날짜 컬럼 옆에 '평일/휴일' 배치
    final_data = []
    for row in raw_data:
        new_row = {}
        for key, value in row.items():
            new_row[key] = value
            # '날짜' 컬럼 다음에 '평일/휴일' 삽입
            if key == '날짜': 
                new_row['평일/휴일'] = row.get('day_type_label')
                
        # 중복 제거 (이미 삽입했으므로 원본 day_type_label은 제외)
        new_row.pop('day_type_label', None)
        final_data.append(new_row)

    return Response(final_data)