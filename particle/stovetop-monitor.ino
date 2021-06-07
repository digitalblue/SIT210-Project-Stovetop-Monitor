// This #include statement was automatically added by the Particle IDE.
#include <HC-SR04.h>
// This #include statement was automatically added by the Particle IDE.
#include <Adafruit_DHT_Particle.h>


#define DHTPIN D6   // what pin we're connected to
#define DHTTYPE DHT22		// DHT 22 (AM2302)

DHT dht(DHTPIN, DHTTYPE);
int led = D7;  // The on-board LED

// HC-SR04 trigger / echo pins
const int triggerPin = D4;
const int echoPin = D5;
HC_SR04 rangefinder = HC_SR04(triggerPin, echoPin);

void setup() {
    pinMode(led, OUTPUT);
  
    Serial.begin(9600); 
    Serial.println("DHTxx test!");
    Particle.publish("state", "DHTxx test start");
    
    rangefinder.init();

    dht.begin();
    delay(2000);
}

void loop() {
    // Read temp and humidity 
    float h = dht.getHumidity();
	float t = dht.getTempCelcius();
	
	// Get distance in centimeters
    float d = rangefinder.distCM();
	
	// Check if any reads failed and exit early (to try again).
	if (isnan(h) || isnan(t) || isnan(d)) {
		Serial.println("Failed to read metrics!");
		return;
	}
    
    digitalWrite(led, HIGH); // Turn ON the LED
    Particle.publish("stovetop_metrics", String::format("{\"hum\": %4.2f, \"temp\": %4.2f, \"dist\": %4.2f}", h, t, d), PRIVATE);
    delay(1000); // Wait for 1 seconds

    digitalWrite(led, LOW); // Turn OFF the LED
    delay(1000); // Wait for 1 seconds
}
