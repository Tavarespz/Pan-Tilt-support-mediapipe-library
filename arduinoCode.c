
#include <Servo.h>

Servo servoX;
Servo servoY;

// ==========================================
// CONFIGURAÇÃO DOS PINOS
// ==========================================
const int pinServoX = 6;
const int pinServoY = 8;

// ==========================================
// VARIÁVEIS DE COMUNICAÇÃO (BUFFER)
// ==========================================
const byte numChars = 16;
char receivedChars[numChars];
boolean newData = false;

void setup() {
  // A velocidade DEVE ser a mesma configurada no Python (115200)
  Serial.begin(115200);
  
  servoX.attach(pinServoX);
  servoY.attach(pinServoY);
  
  // Posição inicial centralizada ao ligar
  servoX.write(90);
  servoY.write(90);
}

void loop() {
  receberDados();
  processarDados();
}

// --------------------------------------------------------
// LÊ A SERIAL CARACTERE POR CARACTERE (NÃO-BLOQUEANTE)
// --------------------------------------------------------
void receberDados() {
  static boolean recvInProgress = false;
  static byte ndx = 0;
  char startMarker = '<';
  char endMarker = '>';
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();

    if (recvInProgress == true) {
      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1; // Previne estouro de buffer (overflow)
        }
      } else {
        receivedChars[ndx] = '\0'; // Termina a string C com caractere nulo
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
    } else if (rc == startMarker) {
      recvInProgress = true;
    }
  }
}

// --------------------------------------------------------
// QUEBRA O TEXTO E MOVE OS MOTORES
// --------------------------------------------------------
void processarDados() {
  if (newData == true) {
    int anguloX = 0;
    int anguloY = 0;
    
    // strtok divide o array de caracteres onde encontrar a vírgula
    char * strtokIndx;

    strtokIndx = strtok(receivedChars, ",");
    if (strtokIndx != NULL) {
      anguloX = atoi(strtokIndx); // Converte o texto do eixo X para inteiro
      
      strtokIndx = strtok(NULL, ",");
      if (strtokIndx != NULL) {
        anguloY = atoi(strtokIndx); // Converte o texto do eixo Y para inteiro

        // Trava de segurança (0 a 180) e envio para os motores
        servoX.write(constrain(anguloX, 0, 180));
        servoY.write(constrain(anguloY, 0, 180));
      }
    }
    
    newData = false; // Libera o sistema para ler o próximo pacote
  }
}
