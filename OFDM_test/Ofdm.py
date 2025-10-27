import numpy as np
import matplotlib.pyplot as plt

# --- 1. 시뮬레이션 파라미터 설정 ---
N_FFT = 64          # FFT 크기 (부반송파 개수)
N_CP = 16           # Cyclic Prefix 길이
N_symbols = 10      # 전송할 OFDM 심볼 개수
MODULATION = 'QPSK' # 변조 방식
SNR_dB = 15        # 신호 대 잡음비 (dB)

# QPSK 심볼 맵핑 (00:1+j, 01:1-j, 10:-1+j, 11:-1-j) / 정규화
qpsk_map = {
    (0,0): (1+1j)/np.sqrt(2),
    (0,1): (1-1j)/np.sqrt(2),
    (1,0): (-1+1j)/np.sqrt(2),
    (1,1): (-1-1j)/np.sqrt(2)
}

# --- 2. 송신부 (Transmitter) ---

# (1) 랜덤 비트 생성
tx_bits = np.random.randint(0, 2, size=(N_FFT * 2 * N_symbols)) # QPSK 이므로 2bit

# (2) QPSK 변조
tx_symbols = []
for i in range(0, len(tx_bits), 2):
    bit_pair = tuple(tx_bits[i:i+2]) # (i,i+1 번째의 위치) 2개씩 자르기
    # tuple 자료형 -> 변경 불가능한 자료형 (?,?)
    tx_symbols.append(qpsk_map[bit_pair])
tx_symbols = np.array(tx_symbols)

# (3) OFDM 심볼 생성 (IFFT + Cyclic Prefix) : 시간단위
ofdm_tx_payload = np.zeros(N_symbols * (N_FFT + N_CP), dtype=complex)
for i in range(N_symbols):
    # 직렬-병렬 변환(serial to parallel)
    symbol_block = tx_symbols[i*N_FFT : (i+1)*N_FFT] 
    # 긴 배열을 subcarrier 묶음으로 잘라 여러 개로 만들기 위해
    
    # IFFT: 주파수 영역 신호를 시간 영역 신호로 변환
    time_signal = np.fft.ifft(symbol_block, N_FFT)
    
    # Cyclic Prefix 추가
    cp = time_signal[-N_CP:] #뒤에서부터 N_CP 만큼 
    ofdm_symbol = np.concatenate([cp, time_signal])
    
    # 전송 페이로드에 저장(parallel to serial)
    ofdm_tx_payload[i*(N_FFT+N_CP) : (i+1)*(N_FFT+N_CP)] = ofdm_symbol

# --- 3. 채널 (Channel) ---

# (1) 신호 전력 계산
signal_power = np.mean(np.abs(ofdm_tx_payload)**2)

# (2) 잡음 전력 계산 (SNR 기반)
snr_linear = 10**(SNR_dB / 10)
noise_power = signal_power / snr_linear

# (3) AWGN 잡음 생성 및 추가 (가우시안 분포)
noise = np.sqrt(noise_power/2) * (np.random.randn(len(ofdm_tx_payload)) + 1j*np.random.randn(len(ofdm_tx_payload)))
ofdm_rx_payload = ofdm_tx_payload + noise


# --- 4. 수신부 (Receiver) ---
rx_symbols = []
for i in range(N_symbols):
    # (1) OFDM 심볼 분리 및 i번째 Cyclic Prefix 제거
    rx_ofdm_symbol = ofdm_rx_payload[i*(N_FFT+N_CP) : (i+1)*(N_FFT+N_CP)] # serial to parallel
    rx_time_signal = rx_ofdm_symbol[N_CP:] #N_CP부터 끝까지 
    
    # (2) FFT: 시간 영역 신호를 주파수 영역 신호로 변환
    freq_signal = np.fft.fft(rx_time_signal, N_FFT)
    rx_symbols.extend(freq_signal) # 현재 rx_symbol은 리스트임

rx_symbols = np.array(rx_symbols) # 수학적 계산의 용이를 위해 np array로 변환

# (3) QPSK 복조
rx_bits = []
for s in rx_symbols:
    # 수신된 심볼과 가장 가까운 QPSK 심볼을 찾아 비트로 변환
    # 결정 규칙: 양수 -> 1, 음수 -> 0
    demod_real = 1 if s.real > 0 else 0
    demod_imag = 1 if s.imag > 0 else 0

    # 미리 부호에 따라 bit 결정 규칙이 존재함
    if demod_real == 1 and demod_imag == 1:       # +1+j 에 가까움 
        rx_bits.extend([1, 1])
    elif demod_real == 1 and demod_imag == 0:     # +1-j 에 가까움 
        rx_bits.extend([1, 0])
    elif demod_real == 0 and demod_imag == 1:     # -1+j 에 가까움
        rx_bits.extend([0, 1])
    else: # demod_real == 0 and demod_imag == 0   # -1-j 에 가까움 
        rx_bits.extend([0, 0])

# --- 5. 성능 평가 및 시각화 ---

# (1) 비트 에러율 (BER) 계산
num_errors = np.sum(tx_bits != rx_bits)
ber = num_errors / len(tx_bits)
print(f"SNR: {SNR_dB} dB")
print(f"Bit Error Rate (BER): {ber:.4f} ({num_errors} / {len(tx_bits)})")

# (2) 성상도 (Constellation) 시각화
plt.figure(figsize=(10,8))
# 송신 신호
plt.subplot(1, 2, 1)
plt.scatter(tx_symbols.real, tx_symbols.imag, marker='o')
plt.title('Transmitted QPSK Constellation')
plt.xlabel('In-Phase')
plt.ylabel('Quadrature')
plt.grid(True)
plt.axis('square')

# 수신 신호
plt.subplot(1, 2, 2)
plt.scatter(rx_symbols.real, rx_symbols.imag, marker='.', alpha=0.5)
plt.title(f'Received QPSK Constellation (SNR={SNR_dB}dB)')
plt.xlabel('In-Phase')
plt.ylabel('Quadrature')
plt.grid(True)
plt.axis('square')

plt.tight_layout()
plt.show()