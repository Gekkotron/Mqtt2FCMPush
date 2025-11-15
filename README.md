# MQTT to FCM Push Notification Service

A Python service that connects to an MQTT broker and sends Firebase Cloud Messaging (FCM) push notifications to Android devices. It supports retrieving FCM tokens from MQTT payloads or from Firestore.

## Features

- 🔌 Connect to any MQTT broker (with optional authentication)
- 📱 Send FCM push notifications to Android devices
- 🔥 Retrieve FCM tokens from Firestore or MQTT payload
- 👥 Support for admin-only notifications
- 🔄 Automatic removal of invalid FCM tokens
- 📝 Comprehensive logging
- ⚙️ Configurable notification priority and TTL

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up Firebase:
   - Create a Firebase project at https://console.firebase.google.com
   - Generate a service account key (Project Settings → Service Accounts → Generate new private key)
   - Save the JSON file and update the path in `config.py`

3. Configure the service:
   - Edit `config.py` with your MQTT broker details
   - Update Firebase credentials path
   - Configure Firestore settings if using token management

## Configuration

Edit `config.py` to configure the service:

```python
# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "notifications/#"
MQTT_USERNAME = None  # Optional
MQTT_PASSWORD = None  # Optional

# Firebase Configuration
FIREBASE_CREDENTIALS = "path/to/firebase-credentials.json"

# Firestore Configuration
USE_FIRESTORE = True  # Use Firestore for token management
FIRESTORE_COLLECTION = "notification"
ADMIN_ONLY = False  # Send only to admin users
```

## Usage

### Running with Docker (Recommended)

#### Quick Start

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Update MQTT broker settings
MQTT_BROKER=your-mqtt-broker.com
MQTT_PORT=1883
MQTT_USERNAME=your-username
MQTT_PASSWORD=your-password

# Ensure credential.json is in the project directory
```

3. Build and run with Docker Compose:
```bash
docker-compose up -d
```

4. View logs:
```bash
docker-compose logs -f mqtt2fcm
```

5. Stop the service:
```bash
docker-compose down
```

#### Using Docker Directly

Build the image:
```bash
docker build -t mqtt2fcm-push .
```

Run the container:
```bash
docker run -d \
  --name mqtt2fcm \
  -e MQTT_BROKER=your-mqtt-broker.com \
  -e MQTT_PORT=1883 \
  -e MQTT_USERNAME=your-username \
  -e MQTT_PASSWORD=your-password \
  -v $(pwd)/credential.json:/app/credential.json:ro \
  mqtt2fcm-push
```

#### Connecting to Local MQTT Broker

If your MQTT broker runs on the host machine, use:

**Option 1: Host network (Linux only)**
```bash
docker run -d \
  --name mqtt2fcm \
  --network host \
  -v $(pwd)/credential.json:/app/credential.json:ro \
  mqtt2fcm-push
```

**Option 2: Use host.docker.internal (Mac/Windows)**
```bash
docker run -d \
  --name mqtt2fcm \
  -e MQTT_BROKER=host.docker.internal \
  -v $(pwd)/credential.json:/app/credential.json:ro \
  mqtt2fcm-push
```

Or update your `.env` file:
```bash
MQTT_BROKER=host.docker.internal
```

### Running Locally (Without Docker)

#### Running the Service

Start the service using:

```bash
python main.py
```

Or run directly:

```bash
python example.py
```

### MQTT Payload Format

When sending notifications via MQTT, use the following JSON structure:

#### Option 1: Using Firestore for tokens (recommended)

Tokens are automatically retrieved from Firestore based on your `ADMIN_ONLY` configuration:

```json
{
  "title": "Alarm Triggered",
  "body": "Motion detected at front door",
  "data": {
    "id": "3",
    "channelId": "Nvr",
    "image_url": "https://orange.blender.org/wp-content/themes/orange/images/common/ed_header.jpg",
    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"
  }
}
```

#### Option 2: Specify tokens in MQTT payload

Override Firestore and send to specific devices by including the `tokens` array:

```json
{
  "title": "Motion Detected",
  "body": "Movement detected in the front yard",
  "tokens": [
    "fcm-token-1",
    "fcm-token-2"
  ],
  "data": {
    "id": "1",
    "channelId": "motion",
    "image_url": "https://test-videos.co.uk/user/pages/images/big_buck_bunny.jpg",
    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
  },
  "priority": "high",
  "ttl": 43200
}
```

#### Real World Example

```json
{
  "title": "Security Alert",
  "body": "Person detected in driveway",
  "data": {
    "id": "5",
    "channelId": "Security",
    "image_url": "https://test-videos.co.uk/user/pages/images/big_buck_bunny.jpg",
    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
  }
}
```

**Note:** When `tokens` is provided in the payload, Firestore is bypassed and notifications are sent only to those specific tokens.

### Firestore Structure

If using Firestore for token management, structure your collection as follows:

**Collection: `notification`** (configurable via `FIRESTORE_COLLECTION` in config.py)

Each document represents a user/device and should contain:

```
notification/
  ├── user1/                          # Document ID (user identifier)
  │   ├── displayName: "John Doe"     # User's display name
  │   ├── device: "Pixel 7"           # Device model/name
  │   ├── admin: true                 # Admin status (optional, defaults to false if missing)
  │   └── tokens: [                   # Array of FCM tokens for this user's devices
  │         "fcm-token-1",
  │         "fcm-token-2"
  │       ]
  │
  ├── user2/
  │   ├── displayName: "Jane Smith"
  │   ├── device: "Samsung S23"
  │   ├── admin: false
  │   └── tokens: ["fcm-token-3"]
  │
  └── user3/                          # User without admin field
      ├── displayName: "Bob Wilson"
      ├── device: "OnePlus 11"
      └── tokens: ["fcm-token-4", "fcm-token-5"]
      # No admin field = treated as admin: false
```

**Required fields:**
- `tokens` (array): List of FCM registration tokens for the user's device(s)

**Optional fields:**
- `displayName` (string): User's name for logging purposes
- `device` (string): Device identifier for logging purposes  
- `admin` (boolean): If `ADMIN_ONLY = True` in config, only users with `admin: true` receive notifications. Users without this field are treated as `admin: false`.

**Example Firestore document:**
```json
{
  "displayName": "John Doe",
  "device": "Pixel 7 Pro",
  "admin": true,
  "tokens": [
    "dXJZ8F9QR_2K...",
    "fKp3mN7Qs_1L..."
  ]
}
```

**Behavior:**
- When MQTT payload has no `tokens` field → service retrieves tokens from all documents in this collection
- If `ADMIN_ONLY = True` → only documents with `admin: true` are included
- Invalid tokens are automatically removed from the `tokens` array after failed delivery attempts

## API Reference

### Mqtt2FCMPush Class

#### Constructor

```python
service = Mqtt2FCMPush(config)
```

**Parameters:**
- `config` (dict): Configuration dictionary

#### Methods

- `connect()`: Connect to MQTT broker
- `start()`: Start the service (blocking)
- `stop()`: Stop the service and disconnect
- `send_fcm_notification(payload)`: Manually send a notification

### Example: Programmatic Usage

```python
from example import Mqtt2FCMPush

config = {
    'mqtt_broker': 'mqtt.example.com',
    'mqtt_port': 1883,
    'mqtt_topic': 'notifications/#',
    'firebase_credentials': 'firebase-creds.json',
    'use_firestore': True,
    'firestore_collection': 'notification',
    'admin_only': False
}

service = Mqtt2FCMPush(config)

# Send a manual notification
service.send_fcm_notification({
    'title': 'Test Notification',
    'body': 'This is a test',
    'tokens': ['your-fcm-token']
})

# Start listening to MQTT
service.start()
```

## Testing

### Testing with Mosquitto

1. Install Mosquitto:
```bash
# macOS
brew install mosquitto

# Ubuntu/Debian
sudo apt-get install mosquitto mosquitto-clients
```

2. Start the service:
```bash
python3 main.py
```

3. Publish a test message (in another terminal):

**Simple test notification:**
```bash
mosquitto_pub -h localhost -t "notifications/test" -m '{
  "title": "Test Notification",
  "body": "This is a test message"
}'
```

**With image and video:**
```bash
mosquitto_pub -h localhost -t "notifications/alarm" -m '{
  "title": "Security Alert",
  "body": "Motion detected at entrance",
  "data": {
    "id": "10",
    "channelId": "Security",
    "image_url": "https://test-videos.co.uk/user/pages/images/big_buck_bunny.jpg",
    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
  }
}'
```

**With specific tokens:**
```bash
mosquitto_pub -h localhost -t "notifications/test" -m '{
  "title": "Direct Message",
  "body": "Sent to specific devices",
  "tokens": ["your-fcm-token-here"],
  "data": {
    "id": "20",
    "channelId": "Test"
  }
}'
```

### Testing FCM Tokens

You can get FCM tokens from your Android app using:

```kotlin
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        Log.d("FCM", "Token: $token")
    }
}
```

## Troubleshooting

### Connection Issues

- Verify MQTT broker address and port
- Check if authentication is required
- Ensure firewall allows connections

### Firebase Issues

- Verify Firebase credentials file path
- Check if service account has proper permissions
- Ensure Firebase project is correctly configured

### Token Issues

- Invalid tokens are automatically logged and removed
- Check Firestore collection name matches configuration
- Verify token format (should be a long alphanumeric string)

### "Successfully sent" but No Notification Received

If you see `Successfully sent: X, Failed: 0` but don't receive notifications on your Android device:

**1. Check Android App FCM Message Handler**

Your Android app MUST handle data messages (not notification messages). This service sends **data-only messages**. Ensure you have a `FirebaseMessagingService`:

```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        // This MUST be implemented to receive data messages
        Log.d("FCM", "Message data: ${remoteMessage.data}")
        
        val title = remoteMessage.data["title"] ?: "Notification"
        val body = remoteMessage.data["body"] ?: ""
        val channelId = remoteMessage.data["channelId"] ?: "default"
        
        // Create and show notification manually
        showNotification(title, body, channelId, remoteMessage.data)
    }
    
    private fun showNotification(title: String, body: String, channelId: String, data: Map<String, String>) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        // Create notification channel for Android O+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                title,
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }
        
        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.drawable.ic_notification)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
}
```

**2. Register Service in AndroidManifest.xml**

```xml
<service
    android:name=".MyFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

**3. Check App State**

- **Background/Killed**: Data messages are only delivered when your app's `FirebaseMessagingService` can handle them
- **Solution**: Ensure your service is properly registered and not being killed by battery optimization

**4. Verify Notification Permissions (Android 13+)**

```kotlin
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
    if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) 
        != PackageManager.PERMISSION_GRANTED) {
        ActivityCompat.requestPermissions(this, 
            arrayOf(Manifest.permission.POST_NOTIFICATIONS), 
            REQUEST_CODE)
    }
}
```

**5. Test Token Validity**

Send a test message directly from Firebase Console (Tools & Settings → Cloud Messaging → Send test message) using the same token. If it doesn't work, the token may be invalid or the app configuration is incorrect.

**6. Check Google Services Configuration**

- Ensure `google-services.json` is in your app module and up to date
- Verify the package name in Firebase Console matches your app's package name
- Confirm Firebase Cloud Messaging API is enabled in Google Cloud Console

**7. Enable Debug Logging**

Add to your Android app:
```kotlin
FirebaseMessaging.getInstance().isAutoInitEnabled = true
```

And check logcat for FCM messages:
```bash
adb logcat | grep -E "(FCM|Firebase)"
```

**Common Issues:**

- ❌ **Using notification payload instead of data payload** - This service sends data-only messages
- ❌ **App not handling data messages** - Must implement `onMessageReceived()`
- ❌ **Notification channel not created** - Required for Android O+
- ❌ **App killed by battery optimization** - Whitelist your app
- ❌ **Missing POST_NOTIFICATIONS permission** - Required for Android 13+

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
