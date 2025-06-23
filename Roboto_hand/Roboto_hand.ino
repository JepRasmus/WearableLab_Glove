// This code is for controlling a robotic hand after having received resistance values from a glove
// The number of fingers involved can be changed by editing num_digits.
// The min and max resistances corresponding to relaxed and maximal bending of the fingers in the glove need to be hardcoded
// Created on 21/06/2025

#include "BLEDevice.h"
#include <Wire.h>

// NeoPixel LED
//#include <Adafruit_NeoPixel.h>
#define LED_PIN    21
#define NUM_LEDS   1
//Adafruit_NeoPixel pixels(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);


/////////////////////////////////// SERVO STUFF ///////////////////////////////////////
// Needed libraries??? - strtok!!!!
#include <stdio.h>
#include <string.h>

#include <ESP32Servo.h>
const int num_digits = 3; // Number of digits

struct digit {
  uint8_t pin; // Pins attached to each servo
  Servo servo; // Servo instances for each digit
  float angle; // Positions on the servo - 0-180 (however - we are using them in other angle spans)
  float raw; // Received resistance values
  uint8_t min_servo_angle;
  uint8_t max_servo_angle;
  float max_resistance; // Set me manually
  float min_resistance; // Set me manually
};


char received_str[100];
digit my_digits[num_digits];

void init_digits(){
  for (int i = 0; i < num_digits ; i++){
    my_digits[i].pin = i+1;
    my_digits[i].servo.attach(my_digits[i].pin);
    my_digits[i].servo.write(90);
  }

  my_digits[0].min_resistance = 160000;
  my_digits[0].max_resistance = 195000;
  my_digits[0].min_servo_angle = 60;
  my_digits[0].max_servo_angle = 140;

  my_digits[1].min_resistance = 135000;
  my_digits[1].max_resistance = 180000;
  my_digits[1].min_servo_angle = 140;
  my_digits[1].max_servo_angle = 60;

  my_digits[2].min_resistance = 170000;
  my_digits[2].max_resistance = 195000;
  my_digits[2].min_servo_angle = 140;
  my_digits[2].max_servo_angle = 60;
}


float floatMap(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

void split_data() { 

  char holder[num_digits][100]; // ## Ensure that each data value is under 1000 chars ## Ensure sent data have number of channels equal to num_digits

  Serial.print("Received data:");
  Serial.println(received_str);

  int i = 0;
  char *pch = strtok(received_str, ","); // Used to split the data
  while (pch != NULL && i < num_digits) {
    strncpy(holder[i], pch, sizeof(holder[i])); // Copy string
    holder[i][sizeof(holder[i]) - 1] = '\0';  // Ensure null termination
    i++;
    pch = strtok(NULL, ",");
  }

  // Only save the firs x datapoints - the stretch sensors
  for (int j = 0; j < i; j++) {
    if (j < num_digits){
      my_digits[j].raw = atof(holder[j]);
      //Serial.println(my_digits[j].raw);;
    }
  }
}


void set_servos(){
  for (int i = 0 ; i < num_digits ; i++){
    my_digits[i].angle = floatMap(my_digits[i].raw, my_digits[i].min_resistance, my_digits[i].max_resistance, my_digits[i].min_servo_angle,  my_digits[i].max_servo_angle);     // scale it to use it with the servo (value between 0 and 180)
    float temp_min = min(my_digits[i].min_servo_angle, my_digits[i].max_servo_angle);
    float temp_max = max(my_digits[i].min_servo_angle, my_digits[i].max_servo_angle);
    my_digits[i].angle = constrain(my_digits[i].angle, temp_min, temp_max); // Constrain to specific angles so we don't overstretch/overbend the fingers
    my_digits[i].servo.write(my_digits[i].angle); // sets the servo position according to the scaled value
    Serial.print("Servo "); Serial.print(i); Serial.print(": "); Serial.println(my_digits[i].angle);
  }
}


/////////////// BLE STUFF ///////////////////////

//BLE Server name (the other ESP32 name running the server sketch)
#define bleServerName "Jeppe is 2 cool"

// UUIDS
static BLEUUID SERVICE_UUID("4fafc201-1fb5-459e-8fcc-c5c9c331914b");
static BLEUUID CHARACTERISTIC_UUID("beb5483e-36e1-4688-b7f5-ea07361b26a8");

//Flags stating if should begin connecting and if the connection is up
static boolean doConnect = false;
static boolean connected = false;

//Address of the peripheral device. Address will be found during scanning...
static BLEAddress *pServerAddress;
 
//Characteristicd that we want to read
static BLERemoteCharacteristic* angleCharacteristic;

//Activate notify ####### What do??
const uint8_t notificationOn[] = {0x1, 0x0};
const uint8_t notificationOff[] = {0x0, 0x0};

bool new_data = false;


//When the BLE Server sends a new temperature reading with the notify property
static void angleNotifyCallback(BLERemoteCharacteristic* pBLERemoteCharacteristic, uint8_t* pData, size_t length, bool isNotify) {
  //store temperature value

  //reveived_str = (char*)pData;
  size_t safe_length = min(length, sizeof(received_str) - 1);
  memcpy(received_str, pData, safe_length);
  received_str[safe_length] = '\0';
  new_data = true;
}

//Connect to the BLE Server that has the name, Service, and Characteristics
bool connectToServer(BLEAddress pAddress) {
   BLEClient* pClient = BLEDevice::createClient();
 
  // Connect to the remove BLE Server.
  pClient->connect(pAddress);
  Serial.println(" - Connected to server");

  pClient->setMTU(100);
  //pClient->setClientCallbacks(new MyClientCallback());
 
  // Obtain a reference to the service we are after in the remote BLE server.
  BLERemoteService* pRemoteService = pClient->getService(SERVICE_UUID);
  if (pRemoteService == nullptr) {
    Serial.print("Failed to find our service UUID: ");
    Serial.println(SERVICE_UUID.toString().c_str());
    return (false);
  }
 
  // Obtain a reference to the characteristics in the service of the remote BLE server.
  angleCharacteristic = pRemoteService->getCharacteristic(CHARACTERISTIC_UUID);
  
  if (angleCharacteristic == nullptr) {
    Serial.print("Failed to find our characteristic UUID");
    return false;
  }
  Serial.println(" - Found our characteristics");
 
  //Assign callback functions for the Characteristics
  angleCharacteristic->registerForNotify(angleNotifyCallback);
  return true;
}

//Callback function that gets called, when another device's advertisement has been received
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    if (advertisedDevice.getName() == bleServerName) { //Check if the name of the advertiser matches
      advertisedDevice.getScan()->stop(); //Scan can be stopped, we found what we are looking for
      pServerAddress = new BLEAddress(advertisedDevice.getAddress()); //Address of advertiser is the one we need
      doConnect = true; //Set indicator, stating that we are ready to connect
      Serial.println("Device found. Connecting!");
    }
  }
};




///////////////////////////////////////// SETUP AND LOOP //////////////////////////////////////////////////


void setup() {
  Serial.begin(115200);
  Serial.println("Starting Arduino BLE Client application...");
  //pixels.begin();
  //pixels.setPixelColor(0, pixels.Color(255, 0, 0)); // RED START
  //pixels.show();
  delay(1000);


  //Init BLE device
  BLEDevice::init("");
 
  // Retrieve a Scanner and set the callback we want to use to be informed when we
  // have detected a new device.  Specify that we want active scanning and start the
  // scan to run for 30 seconds.
  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->start(30);

  init_digits();

  Serial.println("Setup complete!");
}

void loop() {
  // If the flag "doConnect" is true then we have scanned for and found the desired
  // BLE Server with which we wish to connect.  Now we connect to it.  Once we are
  // connected we set the connected flag to be true.
  if (doConnect == true) {
    if (connectToServer(*pServerAddress)) {
      Serial.println("We are now connected to the BLE Server.");
      //Activate the Notify property of each Characteristic
      angleCharacteristic->getDescriptor(BLEUUID((uint16_t)0x2902))->writeValue((uint8_t*)notificationOn, 2, true);
      connected = true;
    } else {
      Serial.println("We have failed to connect to the server; Restart your device to scan for nearby BLE server again.");
    }
    doConnect = false;
  }
  //if new temperature readings are available, print in the OLED
  if (new_data){
    //pixels.setPixelColor(0, pixels.Color(0, 255, 0));
    //pixels.show();
    new_data = false;
    split_data();
    set_servos();
  }
  delay(50);

}
