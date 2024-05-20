# 20240520
- output form: JSON
- 약물이상사례-개별은 복수가 존재할 수 있는데, python code에서는 하나로만 인식해서 값 추출하는 것으로 보임. 수정 필요
- 변수명을 myadr과 동일하게 추출되도록 코드 수정 필요
- 현재 allergyintolerance domain 정보만 포함하고 있음. 전체 patient, organization, practitioner role 등 다른 도메인 포함 한 사례당 전체 HL7 FHIR 리소스 받아야 함
- 샘플자료는 구글 드라이브 공유했음 Bioinformatics\Python\VSCode\FHIR_reverse
