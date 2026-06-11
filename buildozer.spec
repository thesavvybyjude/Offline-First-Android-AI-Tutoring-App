[app]
title = AI Tutor
package.name = aitutor
package.domain = org.tutor
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,gguf,index,db
version = 1.0.0
orientation = portrait
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.entrypoint = org.kivy.android.PythonActivity
