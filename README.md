# CV_Image_Stitching

OpenCV를 이용한 특징점 기반 이미지 정합(Image Stitching) 프로그램입니다.

정합할 이미지들은 `data` 폴더에 `image_stitching1.jpg`, `image_stitching2.jpg`, `image_stitching3.jpg`, ....,  `image_stitchingN.jpg` 형식으로 저장하여 놓아야 제대로된 정합이 가능합니다.

---

## 주요 알고리즘 및 구현 과정

* **특징점 추출 (Feature Extraction)**
  * 크기와 회전에 불변하는 강력한 특징점을 찾기 위해 **SIFT(Scale-Invariant Feature Transform)** 알고리즘을 사용했습니다.
  * 이때, 이전 정합 결과물에 남아있는 검은색 여백(배경)의 모서리를 SIFT가 특징점으로 오인하는 문제를 방지하기 위해 `Threshold` 기반의 마스크(Mask)를 생성하여 **이미지의 유효한 영역 내에서만 특징점을 추출**하도록 처리했습니다.

* **특징점 매칭 (Feature Matching & RANSAC)**
  * **BFMatcher**와 KNN(k=2) 알고리즘을 사용하여 특징점을 매칭했으며, 오탐지를 줄이기 위해 Lowe's Ratio Test(0.75)를 통과한 좋은 매칭점(Good Matches)만 선별했습니다.
  * 이후 **RANSAC** 알고리즘을 통해 잘못 짝지어진 Outlier들을 배제하고, 가장 신뢰성 높은 Homography(원근 변환) 행렬을 도출했습니다.

* **원근 변환 및 동적 캔버스 할당 (Warping & Canvas)**
  * 계산된 Homography 행렬을 바탕으로 `cv.warpPerspective`를 적용하여 이미지를 변형시킵니다.
  * 변형된 이미지가 화면 밖으로 잘려 나가지 않도록 두 이미지의 꼭짓점 좌표를 모두 계산하여 캔버스의 최대 크기를 자동으로 할당(최대 8000px 제한)했습니다. 

* **중앙 앵커 정합 (Center-Anchored Stitching)**
  * 1번 사진부터 순서대로 평면(Planar) 투영을 이어붙일 경우, 시야각이 넓어지면서 양 끝 이미지가 우주 공간으로 빨려 들어가듯 심하게 늘어나는 왜곡이 발생합니다.
  * 이를 해결하기 위해 전체 이미지 리스트의 **중간(Center)에 위치한 사진을 앵커(Anchor)로 삼고**, 양옆으로 퍼져나가며 변환을 수행하도록 순서를 재설계하여 평면 투영의 왜곡을 최대한 방지하였습니다.
  
---

## 주요 기능

* **정합 단계별 화면 전환**
  * 키보드 `Spacebar`를 누를 때마다 **1) 원본 이미지 나열 -> 2) 인접 이미지 간의 특징점 매칭 선 출력 -> 3) 최종 정합된 파노라마 이미지** 순으로 화면이 반복 전환됩니다.
* **자동 해상도 조절**
  * 연산된 파노라마 이미지나 매칭 화면의 해상도가 모니터 크기를 초과할 경우, `cv.imshow` 출력 시 시각적으로 확인하기 편하도록 비율을 유지한 채 최대 높이(900px)로 자동 리사이즈됩니다.
* **프로그램 종료**
  * 키보드 `ESC` 키를 누르면 프로그램이 종료됩니다.

---

## 변환 예시

| Original | Feature points matched | Stitched | 
| :---: | :---: | :---: |
| <img src="https://github.com/user-attachments/assets/d28face9-bab0-4b42-bb8e-b60c744859f7" width="300"> | <img src="https://github.com/user-attachments/assets/b3b4f0d6-1eb0-4229-a0e2-d2afd7e3d7f5" width="300"> | <img src="https://github.com/user-attachments/assets/df5d39dc-6e98-4b6f-a0a2-21a2dc7b3e76" width="300"> |

---

## 문제점 

* **특징점 오탐지 및 매칭의 한계**
  * <img src="https://github.com/user-attachments/assets/1fa0baf6-1bb5-472d-be2a-0a9841bf0e24" width = "900"> 
  * 형광색으로 칠한 부분을 보면 알수 있듯이 건물 창문, 주차장 선, 타일 등 반복되는 패턴이 많거나 조명 변화가 있는 구간에서 SIFT 알고리즘이 특징점을 잘못 매칭하는 경우(False Positive)가 다수 발생했습니다. RANSAC을 통해 필터링을 시도했으나 완벽하게 걸러내지 못하여 정합 결과물의 미세한 왜곡의 원인이 됩니다.
