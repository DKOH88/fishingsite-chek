"""
네이버 카페 양도게시판 모니터 - 콘솔 없이 실행하는 런처
이 .pyw 파일은 pythonw.exe로 실행되어 콘솔 창이 아예 생성되지 않습니다.
"""
import os
import sys

# 현재 파일과 같은 디렉토리를 기준으로 메인 모듈 경로 설정
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# 메인 모듈 실행
exec(open(os.path.join(script_dir, 'BDJ_카페_모니터_GUI.py'), encoding='utf-8').read())
