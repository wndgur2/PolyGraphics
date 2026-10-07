# 인체 캐릭터 레퍼런스 — 프론티어 제품 비교와 표준 비율

> `human.char.wanderer`를 어디에 맞춰 고도화하는지. §1은 측정 기준(해부학·미술 표준), §2는 제품
> 34개의 비교표, §3은 그 표에서 읽어낸 규칙, §4는 그 규칙으로 우리 리그를 감사한 결과와 고친 것.
> 측정은 `scripts/human_audit.py`가 한다 — 관절을 옮겼으면 다시 돌린다.

## 1. 기준

### 1.1 Drillis & Contini (1966) — 성인 평균 분절 길이, 키 대비

생체역학이 쓰는 표준 비례 상수. 키 H에 곱한다.

| 분절 | 비율 | 120px 체격에서 |
| --- | --- | --- |
| 엉덩이 관절(대전자) 높이 | 0.530 | 63.6 |
| 무릎 높이 | 0.285 | 34.2 |
| 어깨 관절 높이 | 0.818 | 98.2 |
| 팔꿈치 높이 | 0.630 | 75.6 |
| 손목 높이 | 0.485 | 58.2 |
| 손끝 높이 | 0.377 | 45.2 |
| 위팔 | 0.186 | 22.3 |
| 아래팔 | 0.146 | 17.5 |
| 손 | 0.108 | 13.0 (주먹은 그 3/4) |
| 허벅지 | 0.245 | 29.4 |
| 정강이(무릎→발목) | 0.246 | 29.5 |
| 발 길이 | 0.152 | 18.2 |
| 발 높이(발목→바닥) | 0.039 | 4.7 |
| 어깨 폭(견봉 간) | 0.259 | 31.1 |
| 엉덩이 폭 | 0.191 | 22.9 |
| 가슴 깊이 | 0.174 | 20.9 |
| 머리+목 | 0.182 | 21.8 |

출처: Drillis & Contini, *Body Segment Parameters* (NYU 1966); PSU OpenLab "Proportionality
constants"; NCSU Ergonomics Center 인체측정 요약표(bideltoid 20.0in, 손 7.6in, 발 10.7in, 팔 벌린 길이 71.3in).

### 1.2 미술 표준 — 머리 단위 (Loomis)

- 평균 성인 **7.5등신**, 이상화된 체격 **8등신**. 게임 영웅은 8 이상이 흔하다.
- 턱 1H · 젖꼭지 2H · 배꼽 3H · 가랑이 4H(8등신 기준; 7.5등신은 3.75H = 키의 정확히 절반) · 무릎 ≈ 5.5~6H · 발바닥 7.5/8H.
- 어깨 폭 2⅓H(남) · 엉덩이 1.5H. 여성은 어깨 2H, 엉덩이 더 넓게.
- 팔꿈치는 허리(배꼽)에, 손목은 가랑이에, 손끝은 허벅지 중간에.
- 흔한 실패: **"long torso syndrome"** — 몸통을 길게, 다리를 짧게 잡는다. 몸의 절반은 허리가 아니라 **가랑이**다.

출처: Proko "Human Proportions – Idealistic Figures (Loomis)".

### 1.3 걷기 (Richard Williams, *The Animator's Survival Kit*)

- 네 자세: **contact → down(recoil) → passing → up**, 한 걸음에 한 번씩, 한 루프에 두 걸음.
- 몸은 contact 직후가 가장 낮고 passing이 가장 높다. 머리는 몸보다 덜 오르내린다.
- 팔은 같은 쪽 다리와 반대 위상. 어깨는 골반과 반대로 돈다. 발은 뒤꿈치→발바닥→발끝 순으로 구른다.

## 2. 제품 비교 — 34개

열: 시점(S 측면 · ¾ 3/4 · T 톱다운 · 3D), 등신(머리 수, 추정은 ≈), 제작 방식, 외곽선, 명암, 우리가 빌릴 것.
"≈"는 공개 스프라이트/스크린샷을 보고 어림한 값이고, 숫자 출처가 있는 것만 각주를 달았다.

| # | 제품 (스튜디오, 연도) | 시점 | 등신 | 방식 | 외곽선 | 명암 | 빌릴 것 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Dead Cells** (Motion Twin 2018) | S | ≈6.5 | 3DS Max 모델 → 커스텀 툴로 픽셀 렌더¹ | 없음(픽셀 경계) | 3D 라이팅, 노멀맵 | 애니메이션 가변성: 리그에서 뽑으니 무기 무게 바꾸면 클립이 따라온다 |
| 2 | **Hades** (Supergiant 2020) | ¾T | ≈8 | 손그림 HD, Mignola·Fred Taylor 영향² | 굵은 검정 | 평면 셀 + 강한 림 | 영웅적 8등신, 큰 실루엣, 빨강 악센트 하나 |
| 3 | **Hades II** (Supergiant 2024) | ¾T | ≈8 | 손그림 HD | 굵은 검정 | 셀 | 동일 |
| 4 | **Dark Souls** (FromSoftware 2011) | 3D | 7.5 | 3D 스캔급 사실 체형 | — | PBR 전 사실 | 7.5등신 사실 비율, 무거운 망토·장화, 검을 아래로 든 자세 |
| 5 | **Bloodborne** (FromSoftware 2015) | 3D | 7.5~8 | 3D | — | 사실 | 코트 자락의 2차 모션, 좁은 어깨의 사냥꾼 실루엣 |
| 6 | **Elden Ring** (FromSoftware 2022) | 3D | 7.5~8 | 3D | — | 사실 | 망토 체인 시뮬레이션 |
| 7 | **Sekiro** (FromSoftware 2019) | 3D | 7.5 | 3D | — | 사실 | 달리기의 상체 기울기(≈12°), 팔 펌프 |
| 8 | **Blasphemous** (The Game Kitchen 2019) | S | ≈7 | 순수 픽셀아트, 셰이더·3D 없음³ | 1px 검정 | 2~3값 | 측면 7등신이 32배 축소에서도 읽히는 값 대비 |
| 9 | **Blasphemous II** (2023) | S | ≈7 | 픽셀아트 | 1px | 3값 | 망토·천의 프레임별 주름 |
| 10 | **Hollow Knight** (Team Cherry 2017) | S | ≈1.5 | 벡터풍 손그림 | 검정 | 평면 | 실루엣 우선; 우리 기준엔 반대 극 |
| 11 | **Hollow Knight: Silksong** (2025) | S | ≈2.5 | 손그림 | 검정 | 평면 | Hornet의 "키가 달라지면 전부 달라진다" |
| 12 | **Castlevania: Symphony of the Night** (Konami 1997) | S | ≈7 | 픽셀아트, Ayami Kojima 디자인⁴ | 1px | 4~5값 | 알루카드 망토: 16방향으로 흔들리는 천의 프레임 |
| 13 | **Castlevania (NES 1986)** | S | ≈4 | 16×16 타일 격자, 3색+1 제한⁵ | 1px | 2값 | 타일에 맞춘 점프 높이 2타일 같은 수치 규칙 |
| 14 | **Street Fighter Alpha 3** (Capcom 1998) | S | ≈7 | 픽셀아트, 류 61×100px⁶ | 1px | 4값 | 100px 높이의 측면 격투 체형 |
| 15 | **Street Fighter III: 3rd Strike** (1999) | S | ≈7.5 | 픽셀아트 | 1px | 5값 | 가장 많은 프레임의 측면 걷기 레퍼런스 |
| 16 | **Guilty Gear Strive** (Arc System Works 2021) | 3D 셀 | ≈8 | 3D + 셀 셰이딩 | 검정 라인 | 2값 셀 | 외곽선 굵기 변화, 앞다리 두꺼운 윤곽 |
| 17 | **Skullgirls** (Lab Zero 2012) | S | ≈8 | 손그림 HD, 캐릭터당 ≈1300프레임⁷ | 검정 | 셀 | 과장된 8등신, 손그림 기준 프레임 수 |
| 18 | **Streets of Rage 4** (Lizardcube 2020) | ¾S | ≈7.5 | 손그림 HD, 캐릭터당 ≈1000프레임⁸ | 검정 | 셀 2값 | 걷기의 어깨 역회전, 손그림 벨트스크롤 3/4 시점 |
| 19 | **Dragon's Crown** (Vanillaware 2013) | S | 6~9 | 손그림 HD | 검정 | 회화 | 직업별 극단적 비율 — 변형의 범위 |
| 20 | **Odin Sphere Leifthrasir** (Vanillaware 2016) | S | ≈7 | 손그림 HD | 검정 | 회화 | 머리카락·치마의 2차 모션 |
| 21 | **13 Sentinels** (Vanillaware 2019) | S | ≈7 | 손그림 HD | 검정 | 회화 | 교복의 주름 묘사 |
| 22 | **Salt and Sanctuary** (Ska Studios 2016) | S | ≈6 | 손그림 | 검정 굵게 | 거칠게 | 다크소울의 2D 번역 — 장비 레이어링 |
| 23 | **Ender Lilies** (Live Wire 2021) | S | ≈6 | 손그림 | 가는 검정 | 부드러운 | 작은 몸과 큰 수호자의 대비 |
| 24 | **Bloodstained: Ritual of the Night** (ArtPlay 2019) | 3D | ≈7 | 3D | — | 사실 | 2.5D 측면 카메라 |
| 25 | **Prince of Persia: The Lost Crown** (Ubisoft 2024) | 3D | ≈7.5 | 3D | — | 셀 | 사르곤의 달리기·구르기 타이밍 |
| 26 | **Ori and the Will of the Wisps** (Moon 2020) | S | ≈2 | 3D 렌더 2D | 없음 | 부드러운 | 반대 극: 점프 유연성 |
| 27 | **Rayman Legends** (Ubisoft 2013) | S | ≈3 | UbiArt 벡터 | 검정 | 평면 | 팔다리 없는 리그 — 우리 반대 극 |
| 28 | **Katana ZERO** (Askiisoft 2019) | S | ≈5.5 | 픽셀아트 | 1px | 3값 | 구르기와 베기의 스미어 프레임 |
| 29 | **Hyper Light Drifter** (Heart Machine 2016) | ¾T | ≈3 | 픽셀아트 | 1px | 2값 | 톱다운 3/4의 망토 |
| 30 | **Octopath Traveler II** (Square Enix 2023) | ¾ | ≈3 | HD-2D | 1px | 2값+조명 | 반대 극 |
| 31 | **Darkest Dungeon** (Red Hook 2016) | S | ≈8+ | 손그림, Mignola 영향 | 굵은 검정 | 평면 | 길쭉한 8등신 이상, 잉크 주름 |
| 32 | **Celeste** (EXOK 2018) | S | ≈2 | 픽셀아트 | 1px | 2값 | 반대 극 |
| 33 | **Terraria** (Re-Logic 2011) | S | ≈2 | 픽셀아트 | 1px | 2값 | 반대 극 |
| 34 | **Chrono Trigger** (Square 1995) | ¾ | ≈3.5 | 픽셀아트 | 1px | 3값 | 반대 극 |

¹ 80.lv 인터뷰: "The models and animation are all done in 3DS Max by one guy", 커스텀 툴로 2D 스프라이트 렌더.
² Wikipedia "Zagreus (Hades)", "Jen Zee": 고전 전통(heroic nudity), Mignola·Fred Taylor 영향.
³ Hollywood Reporter "Blasphemous designer's purist approach": 셰이더·3D 없는 순수 픽셀아트.
⁴ Wikipedia "Alucard (Castlevania)".
⁵ slynyrd Pixelblog 37 "Classic Castlevania Study": 16×16 타일, 점프 2타일, 스프라이트 3색+1.
⁶ ChronoCrash 포럼 "How big should sprites be?": SFA3 류 61×100px, 격투 스프라이트 70~100px.
⁷ skullgirls.com "On Animation in Skullgirls": 캐릭터당 평균 ≈1300 손그림 프레임.
⁸ PlayStation Blog "How Lizardcube redesigned…": 캐릭터당 ≈1000 프레임, 적 300~400.

## 3. 표에서 읽은 규칙

1. **목표 군(Dead Cells·Dark Souls·Hades)은 7~8등신이다.** 2~4등신 군(Hollow Knight, Celeste, Octopath)은 다른 문법이고, 우리 문서는 7.5등신 사실 체형 + 8등신 쪽으로 기운 영웅적 어깨를 택한다.
2. **측면 또는 3/4 측면.** 측면 전용(SF, Blasphemous)은 걷기가 가장 잘 읽히고, 3/4(SoR4, Hades)은 가슴과 양팔이 보인다. 우리는 3/4 측면: 몸통 25° 회전, 다리는 거의 측면.
3. **손그림 HD 군은 셀 2값 + 검정 외곽선**, 픽셀 군은 1px 외곽선 + 3~5값. 우리는 벡터이므로 "thin 잉크 실루엣 + hair 잉크 내부 + 재질당 3값(+림)"이 양쪽의 교집합이다.
4. **악센트는 하나.** Hades의 빨강, Dead Cells의 주황 머리, Blasphemous의 금. 우리는 후드 안감 크림슨.
5. **천은 리그로 흔든다.** 알루카드 망토, 오딘 스피어의 머리카락, 엘든 링의 체인 시뮬 — 전부 몸보다 한 박자 늦는다. 우리 망토 3마디 체인이 그 역할.
6. **클립 수는 수백 프레임 단위.** SoR4 1000·Skullgirls 1300 손그림 프레임. 리그에서 뽑는 우리는 샘플 밀도(keyset 16~30)로 같은 매끄러움을 얻고, 비용은 0이다 — Dead Cells가 3D 리그를 택한 이유와 같다.
7. **달리기 상체 기울기 10~15°, 걷기 3~5°.** 세키로·SoR4·Dead Cells 전부 이 범위.

## 4. 감사 — 우리 리그가 어디서 어긋났나

`python3 scripts/human_audit.py`, 패스 6 직후:

| 항목 | 리그 | 표준 | 차이 |
| --- | --- | --- | --- |
| 엉덩이 관절 높이 / 키 | 0.500 | 0.530 | **−3.0%** ▲ |
| 정강이 / 키 | 0.221 | 0.246 | −2.5% |
| 아래팔 / 키 | 0.158 | 0.146 | +1.2% |
| 위팔 / 키 | 0.175 | 0.186 | −1.1% |
| 어깨 라인(화면) | 10.2 | 13.1 | −2.9px |
| 엉덩이 관절 간격(화면) | 4.1 | 9.7 | **−5.6px** ▲ |
| 가랑이, 머리 단위 | 4.06H | 3.75H | **+0.3H** ▲ |

읽기: 전형적인 **long torso** — 엉덩이 관절을 가랑이 높이(0.5H)에 뒀는데 대전자는 가랑이보다
위(0.53H)다. 그만큼 다리가 짧고 몸통이 길었다. 아래팔은 길고 위팔은 짧았으며(손목이 가랑이보다
아래), 어깨와 엉덩이가 좁아 몸이 기둥처럼 읽혔다.

고친 것(패스 7): 엉덩이 관절 y 0 → −4 · 허벅지 28.5 → 29.5 · 정강이 26.5 → 29 · 발 높이 6 → 5 ·
위팔 21 → 22.3 · 아래팔 19 → 17.5 · 어깨 (−6.4, −37)/(6.4, −39.2) · 엉덩이 관절 ±4. 사지
폴리곤은 `stretch()`로 길이 비율만큼 늘였고, 골반 덩어리·벨트·주머니·카울·브로치가 관절을
따라 올라갔다. 감사 후: 20개 중 주먹(펼친 손 기준의 손끝 높이)만 허용치 밖.

바닥 대비(`readability.ts`)는 의상을 입히자 4.4 → 1.43으로 떨어졌다(어두운 가죽·천이 어두운 돌에 가라앉음). 표의 규칙 4·
§3-3대로 주인공을 바닥보다 밝은 쪽으로: 팔레트 전체를 한 단계 올려 2.26(기준 2.0 위).

머리 단위 격자를 렌더 위에 겹쳐 본 것: 턱 1H, 어깨 1.4H, 벨트 3H, 가랑이 3.8H, 장화 커프(무릎)
5.5H, 발바닥 7.5H.
