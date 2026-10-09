#include <Arduino.h>

// --------------------------------------------------
// Nano -> Raspberry Pi GPIO mapping
// --------------------------------------------------

const uint8_t inputPins[7] = {
  2, 3, 4, 5, 6, 7, 8
};

const uint8_t inputGpios[7] = {
  42, 43, 44, 45, 46, 47, 48
};

const uint8_t outputPins[5] = {
  9, 10, 11, 12, 13
};

const uint8_t outputGpios[5] = {
  39, 49, 50, 51, 52
};


// --------------------------------------------------
// Event queue
// --------------------------------------------------

struct GPIOEvent {
  uint8_t gpio;
  uint8_t state;
};

const uint8_t QUEUE_SIZE = 32;

volatile GPIOEvent eventQueue[QUEUE_SIZE];

volatile uint8_t queueHead = 0;
volatile uint8_t queueTail = 0;


// --------------------------------------------------
// Input interrupt handlers
// --------------------------------------------------

void inputISR0() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 42;
    eventQueue[queueHead].state = digitalRead(2);
    queueHead = next;
  }
}

void inputISR1() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 43;
    eventQueue[queueHead].state = digitalRead(3);
    queueHead = next;
  }
}

void inputISR2() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 44;
    eventQueue[queueHead].state = digitalRead(4);
    queueHead = next;
  }
}

void inputISR3() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 45;
    eventQueue[queueHead].state = digitalRead(5);
    queueHead = next;
  }
}

void inputISR4() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 46;
    eventQueue[queueHead].state = digitalRead(6);
    queueHead = next;
  }
}

void inputISR5() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 47;
    eventQueue[queueHead].state = digitalRead(7);
    queueHead = next;
  }
}

void inputISR6() {
  uint8_t next = (queueHead + 1) % QUEUE_SIZE;

  if (next != queueTail) {
    eventQueue[queueHead].gpio = 48;
    eventQueue[queueHead].state = digitalRead(8);
    queueHead = next;
  }
}


// --------------------------------------------------
// Send compact binary event
//
// Packet:
//
// 0xAA
// GPIO
// STATE
// CRC
// --------------------------------------------------

void sendEvent(uint8_t gpio, uint8_t state)
{
  uint8_t crc = 0xAA ^ gpio ^ state;

  Serial.write(0xAA);
  Serial.write(gpio);
  Serial.write(state);
  Serial.write(crc);
}


// --------------------------------------------------
// Process incoming RPi command
//
// Expected packet:
//
// 0x55
// GPIO
// STATE
// CRC
// --------------------------------------------------

void processSerial()
{
  static uint8_t buffer[4];
  static uint8_t index = 0;

  while (Serial.available())
  {
    uint8_t byteReceived = Serial.read();

    if (index == 0)
    {
      if (byteReceived == 0x55)
      {
        buffer[index++] = byteReceived;
      }

      continue;
    }

    buffer[index++] = byteReceived;

    if (index == 4)
    {
      uint8_t gpio = buffer[1];
      uint8_t state = buffer[2];
      uint8_t crc = buffer[3];

      uint8_t expectedCRC =
        0x55 ^ gpio ^ state;

      if (crc == expectedCRC)
      {
        for (uint8_t i = 0; i < 5; i++)
        {
          if (outputGpios[i] == gpio)
          {
            digitalWrite(
              outputPins[i],
              state ? HIGH : LOW
            );

            break;
          }
        }
      }

      index = 0;
    }
  }
}


// --------------------------------------------------
// Send queued GPIO events
// --------------------------------------------------

void processEvents()
{
  while (true)
  {
    noInterrupts();

    if (queueTail == queueHead)
    {
      interrupts();
      break;
    }

  GPIOEvent event;

  event.gpio = eventQueue[queueTail].gpio;
  event.state = eventQueue[queueTail].state;

  queueTail =
    (queueTail + 1) % QUEUE_SIZE;
    interrupts();

    sendEvent(
      event.gpio,
      event.state
    );
  }
}


// --------------------------------------------------
// Setup
// --------------------------------------------------

void setup()
{
  Serial.begin(115200);

  // Inputs
  for (uint8_t i = 0; i < 7; i++)
  {
    pinMode(
      inputPins[i],
      INPUT
    );
  }

  // Outputs
  for (uint8_t i = 0; i < 5; i++)
  {
    pinMode(
      outputPins[i],
      OUTPUT
    );

    digitalWrite(
      outputPins[i],
      LOW
    );
  }


  // Interrupts
  attachInterrupt(
    digitalPinToInterrupt(2),
    inputISR0,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(3),
    inputISR1,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(4),
    inputISR2,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(5),
    inputISR3,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(6),
    inputISR4,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(7),
    inputISR5,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(8),
    inputISR6,
    CHANGE
  );
}


// --------------------------------------------------
// Main loop
// --------------------------------------------------

void loop()
{
  processSerial();

  processEvents();
}