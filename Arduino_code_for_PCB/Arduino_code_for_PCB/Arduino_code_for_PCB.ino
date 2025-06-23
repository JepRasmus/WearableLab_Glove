/******************************************
*************************************
 * Example: BLE + (Resistance + IMU) in ONE Characteristic
 ******************************************************************************/

//#include <Wire.h>
// SparkFun LSM6DSO library
//#include <SparkFunLSM6DSO.h>
//LSM6DSO myIMU;  // IMU object

// ESP32 BLE libraries
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// NeoPixel LED
#include <Adafruit_NeoPixel.h>
#define LED_PIN    21
#define NUM_LEDS   1
Adafruit_NeoPixel pixels(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// BLE objects/flags
BLEServer* pServer                = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// Use one service/characteristic for both sets of data
#define SERVICE_UUID          "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID   "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// ADC definitions
const int NUM_CHANNELS = 6;
const int ADC_PINS[NUM_CHANNELS] =  {6, 10, 11, 1, 2, 3}; //{1, 2, 3, 4, 5, 6, 10, 11, 12, 13}; // {6, 10, 11};

// Known fixed resistor in ohms
const float R_TOP_100k    = 100000.0;
const float R_TOP_4k       = 4200.0;
const float SUPPLY_VOLTAGE = 3.3;  // 3.3 V

/*******************************************************************************
 * BLE Server Callbacks
 ******************************************************************************/
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
     deviceConnected = true;
   }
   void onDisconnect(BLEServer* pServer) {
     deviceConnected = false;
    // Restart advertising when disconnected
     BLEDevice::startAdvertising();
   }
};

/*******************************************************************************
 * setup()
 ******************************************************************************/
void setup() {
  Serial.begin(115200);

  // Initialize NeoPixel LED, set to red on startup
  pixels.begin();
  pixels.setPixelColor(0, pixels.Color(255, 0, 0));
  pixels.show();

  // 1. Initialize I2C
  //Wire.begin(8, 9); // SDA=8, SCL=9 (if your board supports these pins for I2C)

  // 2. Initialize LSM6DSO (SparkFun library) over I2C
  // Pass address and Wire object: 0x6A or 0x6B depending on your hardware
  //if (!myIMU.begin(0x6A, Wire)) { 
  //  Serial.println("LSM6DSO init failed! Check wiring/address.");
  //  while (1) delay(10);
  //}

  // Configure IMU ranges (optional)
  //myIMU.setAccelRange(8);   // ±2G
  //myIMU.setGyroRange(2000);  // ±250 dps

  // 3. Initialize BLE
  BLEDevice::init("Jeppe is 2 cool");
  BLEDevice::setMTU(100);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  
  // Create one service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create ONE characteristic for combined data
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();
  
  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06); // helps with iPhone connection
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  
  // Set ADC resolution to 12-bit
  analogReadResolution(12);

  // Blue LED once BLE is ready (advertising)
  pixels.setPixelColor(0, pixels.Color(0, 0, 255));
  pixels.show();

  Serial.println("BLE (Resistance + IMU in 1 characteristic) Ready");
}

/*******************************************************************************
 * loop()
 ******************************************************************************/
void loop() {
  if (deviceConnected) {
    // Green LED when connected
    pixels.setPixelColor(0, pixels.Color(0, 255, 0));
    pixels.show();
    
    /****************************************************
     * 1. Read ADC → Resistance
     ****************************************************/
    String resValues; 
    for (int i = 0; i < NUM_CHANNELS; i++) {
      int raw = analogRead(ADC_PINS[i]); // 0..4095
      float voltage = (SUPPLY_VOLTAGE * raw) / 4095.0;

      float resistance = 0.0;
      if (voltage < SUPPLY_VOLTAGE) {
        // R_meas = R_top * (V / (3.3 - V))
        if(i > 3){
          resistance = (R_TOP_4k * voltage) / (SUPPLY_VOLTAGE - voltage);
        } else {
          resistance = (R_TOP_100k * voltage) / (SUPPLY_VOLTAGE - voltage);
        }
      } else {
        // near 3.3 => infinite
        resistance = -1;
      }

      if(resistance > 1000000){
        resistance = 1000000;
      }

      // Build CSV of Resistances
      resValues += String(resistance, 1);
      if (i < NUM_CHANNELS - 1) resValues += ",";
    }

    /****************************************************
     * 2. Read LSM6DSO IMU
     ****************************************************/
    //float ax = myIMU.readFloatAccelX();
    //float ay = myIMU.readFloatAccelY();
    //float az = myIMU.readFloatAccelZ();
    //float gx = myIMU.readFloatGyroX();
    //float gy = myIMU.readFloatGyroY();
    //float gz = myIMU.readFloatGyroZ();
    //float tempC = myIMU.readTempC();

    // Build CSV for IMU: ax,ay,az,gx,gy,gz,temp
    //String imuValues = String(ax, 4) + "," +
                       //String(ay, 4) + "," +
                       //String(az, 4) + "," +
                       //String(gx, 4) + "," +
                       //String(gy, 4) + "," +
                       //String(gz, 4) + "," +
                       //String(tempC, 2);

    /****************************************************
     * 3. Combine both into ONE string
     ****************************************************/
    // Example:  "RES=...,...,... | IMU=...,...,..."
    // Or just a single CSV with all fields. 
    // Here, we'll do a simple combined string.
    // Format it however you like, e.g.:
    //   "ADC:2.34,3.45,...|IMU:0.1234,0.5678,..."
    String combinedData = resValues ; //+ "," + imuValues;

    // Send that combined string in one characteristic notify
    pCharacteristic->setValue(combinedData.c_str());
    pCharacteristic->notify();

    // Debug
    Serial.println(combinedData);

    // Optional small delay to not overload BLE
    //delay(50);

  } else {
    // Blue LED when advertising (not connected)
    pixels.setPixelColor(0, pixels.Color(0, 0, 255));
    pixels.show();
    //delay(50);
  }
  delay(50);
}
