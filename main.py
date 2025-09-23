
import librosa
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Load audio
file_path = "sample.wav"  # 
y, sr = librosa.load(file_path, sr=16000)
print(f"Audio shape: {y.shape}, Sample rate: {sr}")

# Step 2: Extract MFCC features
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
print("MFCC shape:", mfcc.shape)

# Step 3: Plot MFCC
plt.figure(figsize=(10, 4))
librosa.display.specshow(mfcc, x_axis='time')
plt.colorbar()
plt.title("MFCC Features")
plt.show()

