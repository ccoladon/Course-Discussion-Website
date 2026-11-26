# Flutter mobile apps

Patterns and conventions for building Android + iOS apps with Flutter. The Flutter project lives in the `app/` subdirectory alongside the Django backend in `site/`.

## Toolchain

| Layer | Choice | Pin location |
|---|---|---|
| Language | Dart via Flutter SDK | `app/pubspec.yaml` → `environment.sdk` |
| UI framework | Flutter + Material Design 3 | `app/pubspec.yaml` → `flutter` |
| HTTP client | `package:http` | `app/pubspec.yaml` |
| State management | `package:provider` | `app/pubspec.yaml` |
| Camera/gallery | `package:image_picker` | `app/pubspec.yaml` |
| Secure storage | `package:flutter_secure_storage` | `app/pubspec.yaml` |
| Image caching | `package:cached_network_image` | `app/pubspec.yaml` |
| Sharing | `package:share_plus` | `app/pubspec.yaml` |
| Location | `package:geolocator` | `app/pubspec.yaml` |

Dependencies use `^` constraints (compatible version ranges). Reproducibility comes from `app/pubspec.lock` — commit it.

## Project structure

```
app/
  lib/
    main.dart                  # App entry point, Provider setup, MaterialApp routes
    src/
      api/
        client.dart            # HTTP client with auth token handling
      screens/                 # One file per screen (home, auth, detail, ...)
      widgets/                 # Reusable widgets
  test/
```

### Auth flow (token-based)

1. Enter email → call the OTP login endpoint → allauth sends an OTP code
2. Enter code → call the login confirm endpoint → returns a DRF token key
3. Store token in `flutter_secure_storage`
4. All subsequent requests include `Authorization: Token <key>`

See `PROJECT.md` for this project's concrete endpoint paths.

Token storage uses `flutter_secure_storage` which encrypts on both Android (EncryptedSharedPreferences) and iOS (Keychain).

## Android build

### Files

- `app/android/settings.gradle.kts` — plugin versions (AGP, Kotlin)
- `app/android/build.gradle.kts` — build output directory
- `app/android/app/build.gradle.kts` — app config: namespace, SDK versions, signing
- `app/android/gradle/wrapper/gradle-wrapper.properties` — Gradle distribution URL

### Version pins

Current baseline (Flutter 3.44 / Aug 2026):

| Component | Version | Location |
|---|---|---|
| Android Gradle Plugin | 9.0.1 | `app/android/settings.gradle.kts` |
| Kotlin | 2.3.20 | `app/android/settings.gradle.kts` |
| Gradle | 9.1.0 | `app/android/gradle-wrapper.properties` |
| Java target | 17 | `app/android/app/build.gradle.kts` |

These should match whatever `flutter create` generates for the current stable Flutter.

### Signing

Debug build uses the auto-generated debug keystore. For release builds, set up a signing config in `app/android/app/build.gradle.kts`. Store the keystore file outside the repo. Never commit it.

## iOS build

### Files

- `app/ios/Podfile` — CocoaPods integration
- `app/ios/Runner.xcodeproj/project.pbxproj` — Xcode project config
- `app/ios/Runner/Info.plist` — bundle display name, permissions

### Signing

A free Apple ID is sufficient for development. Setup in Xcode:
1. Xcode → Settings → Accounts → + → Apple ID → sign in
2. Open `app/ios/Runner.xcworkspace` in Xcode
3. Select Runner target → Signing & Capabilities → Team → pick your Apple ID

### Deployment target

Set `platform :ios, '13.0'` in `app/ios/Podfile` and `IPHONEOS_DEPLOYMENT_TARGET = 13.0;` in the Xcode project.

### Bundle identifier

Set in two places — keep them in sync:
- `app/android/app/build.gradle.kts` → `applicationId`
- `app/ios/Runner.xcodeproj/project.pbxproj` → `PRODUCT_BUNDLE_IDENTIFIER`

## Development workflow

```bash
# All commands run from app/
cd app

# List devices
flutter devices

# Run on device (debug, hot-reloadable)
flutter run -d <device-id>

# Run on device (release)
flutter run --release -d <device-id>

# Code quality
flutter analyze
flutter clean
```

## API keys and secrets

For Flutter apps, API keys in the client binary are visible to anyone who decompiles the APK/IPA. Projects on this stack handle this by:
- The Django backend holds all secrets (R2, Resend, DB)
- The Flutter app only gets a per-user DRF auth token
- No service tokens, API keys, or credentials are embedded in the mobile app

## Reference files

- `app/pubspec.yaml` — dependencies, SDK constraint
- `app/pubspec.lock` — reproducible dependency resolution (commit it)
- `app/lib/src/api/client.dart` — API client with auth
- `app/lib/src/screens/` — all screen implementations
- `app/android/app/build.gradle.kts` — Android app config
- `app/ios/Runner.xcodeproj/project.pbxproj` — Xcode project
