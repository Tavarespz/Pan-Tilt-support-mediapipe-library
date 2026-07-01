import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import serial
import time

# ==========================================
# 1. CONFIGURAÇÃO DA COMUNICAÇÃO SERIAL
# ==========================================
usar_serial = True
porta_serial = 'COM3'
baud_rate = 115200

if usar_serial:
    try:
        arduino = serial.Serial(porta_serial, baud_rate)
        time.sleep(2)
        print("Arduino conectado com sucesso!")
    except Exception as e:
        print(f"Erro ao conectar no Arduino: {e}")
        usar_serial = False

# ==========================================
# 2. CONFIGURAÇÃO DO DETECTOR DE ROSTO (MEDIAPIPE)
# ==========================================
base_options = python.BaseOptions(
    model_asset_path="face_landmarker.task"
)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1
)

detector = vision.FaceLandmarker.create_from_options(options)

# ==========================================
# 3. VARIÁVEIS DE CONTROLE E ESTABILIZAÇÃO
# ==========================================
servo_x_atual = 90.0
servo_y_atual = 90.0
suavizacao = 0.05  # filtro elástico: quanto menor, mais suave (e mais "atrasado")

# Campo de visão (ajuste conforme a sua lente/distância da câmera)
# Esses valores definem o quanto o servo se move de ponta a ponta da imagem.
# Se o rastreamento estiver "curto" (não acompanha o rosto até a borda),
# aumente. Se estiver "nervoso"/exagerado, diminua.
FOV_X = 110
FOV_Y = 110

min_angulo_x = 90 - (FOV_X // 2)
max_angulo_x = 90 + (FOV_X // 2)
min_angulo_y = 90 - (FOV_Y // 2)
max_angulo_y = 90 + (FOV_Y // 2)

offset_y = 0


def mapear_valor(valor, entrada_min, entrada_max, saida_min, saida_max):
    return int(
        (valor - entrada_min) * (saida_max - saida_min)
        / (entrada_max - entrada_min) + saida_min
    )


def get_face_center(results, width, height):
    if not results.face_landmarks:
        return None
    face = results.face_landmarks[0]
    nose = face[1]  # ponta do nariz
    x = int(nose.x * width)
    y = int(nose.y * height)
    return x, y


# ==========================================
# 4. LOOP PRINCIPAL
# ==========================================
camera = cv2.VideoCapture(0)  # confira se o índice é 0, 1 ou 2 na câmera nova
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Confirma a resolução que a câmera de fato aplicou
largura_real = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
altura_real = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
print(f"Resolução aplicada pela câmera: {largura_real}x{altura_real}")

print("Iniciando rastreamento de ROSTO estabilizado... Pressione 'Q' para sair.")

while True:
    sucesso, frame = camera.read()
    if not sucesso:
        break


    altura_tela, largura_tela, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    results = detector.detect(mp_image)

    face_center = get_face_center(results, largura_tela, altura_tela)

    # Ignora a detecção se o rosto estiver muito perto da borda da imagem —
    # é onde a landmark do nariz fica mais instável (rosto parcialmente cortado)
    MARGEM_BORDA = 0.05  # 5% da largura/altura
    if face_center is not None:
        cx, cy = face_center
        if (
            cx < largura_tela * MARGEM_BORDA
            or cx > largura_tela * (1 - MARGEM_BORDA)
            or cy < altura_tela * MARGEM_BORDA
            or cy > altura_tela * (1 - MARGEM_BORDA)
        ):
            face_center = None

    if face_center is not None:
        centro_x, centro_y = face_center

        # Mapeamento DIRETO da posição do rosto na tela para um ângulo
        # dentro do FOV definido (não é correção por erro acumulado)
        alvo_x = mapear_valor(
            centro_x, 0, largura_tela, max_angulo_x, min_angulo_x
        )
        alvo_y = mapear_valor(
            centro_y, 0, altura_tela, min_angulo_y, max_angulo_y
        )

        alvo_y = max(min_angulo_y, min(max_angulo_y, alvo_y + offset_y))
        alvo_x = max(min_angulo_x, min(max_angulo_x, alvo_x))

        # Suavização aplicada no ângulo final
        servo_x_atual = (alvo_x * suavizacao) + (servo_x_atual * (1.0 - suavizacao))
        servo_y_atual = (alvo_y * suavizacao) + (servo_y_atual * (1.0 - suavizacao))

        ang_x, ang_y = int(servo_x_atual), int(servo_y_atual)

        # Desenho na tela
        cv2.circle(frame, (centro_x, centro_y), 6, (0, 0, 255), -1)
        cv2.putText(
            frame,
            f"Pan: {ang_x}  Tilt: {ang_y}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        # Envia o comando ao Arduino a cada frame (sem threshold/intervalo,
        # igual à abordagem do código Haar)
        if usar_serial:
            arduino.write(f"<{ang_x},{ang_y}>\n".encode('utf-8'))

    cv2.imshow("Pan-Tilt Rosto Estabilizado", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()
if usar_serial:
    arduino.close()
