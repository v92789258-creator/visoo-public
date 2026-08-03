#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <filesystem>
#include <fstream>
#include "picosha2.h"
#include "fast_checksums.h"

namespace py = pybind11;
namespace fs = std::filesystem;

// Implementación de la función declarada en fast_checksums.h
std::map<std::string, std::string> fast_checksums::directory_checksums(const std::string& path_str) {
    std::map<std::string, std::string> result;
    try {
        fs::path base(path_str);
        if (!fs::exists(base) || !fs::is_directory(base)) {
            throw std::runtime_error("Path does not exist or is not a directory: " + path_str);
        }
        for (auto &entry : fs::recursive_directory_iterator(base)) {
            try {
                if (fs::is_regular_file(entry.path())) {
                    std::ifstream ifs(entry.path(), std::ios::binary);
                    if (!ifs) continue;
                    std::vector<unsigned char> buffer((std::istreambuf_iterator<char>(ifs)), std::istreambuf_iterator<char>());
                    std::string hex = picosha2::hash256_hex_string(buffer.begin(), buffer.end());
                    std::string rel = fs::relative(entry.path(), base).generic_string();
                    result[rel] = hex;
                }
            } catch (const std::exception &e) {
                // skip file on error
            }
        }
    } catch (const std::exception &e) {
        throw;
    }
    return result;
}

PYBIND11_MODULE(fast_checksums, m) {
    m.doc() = "fast_checksums: compute sha256 checksums for files in a directory";
    m.def("directory_checksums", &fast_checksums::directory_checksums, "Compute SHA256 checksums for all files under a directory (returns dict relative_path -> hex)", py::arg("path"));
}
