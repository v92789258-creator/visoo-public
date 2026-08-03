// picosha2: a compact single-file SHA256 implementation header
// Minimal public-domain style header suitable for small projects / PoC
// Source: adapted from picosha2 (https://github.com/okdshin/PicoSHA2) with small helper functions

#ifndef PICOSHA2_H
#define PICOSHA2_H

#include <vector>
#include <string>
#include <iterator>
#include <sstream>
#include <iomanip>

namespace picosha2 {

inline std::string to_hex_string(const std::vector<unsigned char>& v) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (unsigned char c : v) {
        oss << std::setw(2) << (int)c;
    }
    return oss.str();
}

// A tiny SHA-256 implementation based on a public-domain reference.
// Note: this is intentionally compact and not optimized for large files — OK for PoC.

// --- Begin minimal SHA256 ---

using uint32 = unsigned int;

inline uint32 rotr(uint32 x, uint32 n) {
    return (x >> n) | (x << (32 - n));
}

inline void sha256_transform(const unsigned char* chunk, uint32 state[8]) {
    static const uint32 k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32 w[64];
    for (int i = 0; i < 16; ++i) {
        w[i] = (uint32)chunk[i*4] << 24 | (uint32)chunk[i*4+1] << 16 | (uint32)chunk[i*4+2] << 8 | (uint32)chunk[i*4+3];
    }
    for (int i = 16; i < 64; ++i) {
        uint32 s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3);
        uint32 s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint32 a = state[0], b = state[1], c = state[2], d = state[3], e = state[4], f = state[5], g = state[6], h = state[7];
    for (int i = 0; i < 64; ++i) {
        uint32 S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
        uint32 ch = (e & f) ^ ((~e) & g);
        uint32 temp1 = h + S1 + ch + k[i] + w[i];
        uint32 S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
        uint32 maj = (a & b) ^ (a & c) ^ (b & c);
        uint32 temp2 = S0 + maj;
        h = g; g = f; f = e; e = d + temp1; d = c; c = b; b = a; a = temp1 + temp2;
    }
    state[0] += a; state[1] += b; state[2] += c; state[3] += d; state[4] += e; state[5] += f; state[6] += g; state[7] += h;
}

inline std::vector<unsigned char> sha256(const std::vector<unsigned char>& data) {
    uint32 state[8] = {
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    };
    std::vector<unsigned char> padded = data;
    uint64_t bit_len = (uint64_t)data.size() * 8ULL;
    // append 0x80
    padded.push_back(0x80);
    // pad with zeros until length ≡ 56 mod 64
    while ((padded.size() % 64) != 56) padded.push_back(0x00);
    // append length big-endian
    for (int i = 7; i >= 0; --i) padded.push_back((bit_len >> (8*i)) & 0xff);
    for (size_t i = 0; i < padded.size(); i += 64) {
        sha256_transform(&padded[i], state);
    }
    std::vector<unsigned char> digest(32);
    for (int i = 0; i < 8; ++i) {
        digest[i*4] = (state[i] >> 24) & 0xff;
        digest[i*4+1] = (state[i] >> 16) & 0xff;
        digest[i*4+2] = (state[i] >> 8) & 0xff;
        digest[i*4+3] = (state[i]) & 0xff;
    }
    return digest;
}

template<typename It>
inline std::string hash256_hex_string(It first, It last) {
    std::vector<unsigned char> data;
    for (auto it = first; it != last; ++it) data.push_back((unsigned char)*it);
    auto digest = sha256(data);
    return to_hex_string(digest);
}

// Convenience overloads
inline std::string hash256_hex_string(const std::vector<unsigned char>& v) {
    return to_hex_string(sha256(v));
}

// --- End minimal SHA256 ---

} // namespace picosha2

#endif // PICOSHA2_H
