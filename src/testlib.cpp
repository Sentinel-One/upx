#ifdef _MSC_BUILD
#include <windows.h>
#include <filesystem>
#else
#include <dirent.h>
#include <experimental/filesystem>
#endif

#include <stdint.h>
#include <vector>
#include <fstream>
#include <cstring>
#include <memory>
#include <utility>

#include "upxlib.h"

using namespace std;
using namespace experimental::filesystem::v1;

int read_entire_file(const path file_name,
                     vector<char> & file_data_out,
                     size_t & size)
{
    ifstream file(file_name, ios::binary | ios::ate);
    size = static_cast<size_t>(file.tellg());

    if (!file.is_open()) {
        perror("Error opening file");
        return 1;
    }

    if (size <= 0 || 1024 * 1024 * 64 < size) {
        perror("Invalid file size");
        return 2;
    }
    uint32_t paddingSize = 8 - (size & 7);

    file_data_out.resize(static_cast<unsigned int>(size + paddingSize));

    file.seekg(0, ios::beg);
    if (!file.read(file_data_out.data(), size)) {
        perror("Error reading file");
        return 3;
    }

    if (0 != paddingSize) {
        std::memset(&file_data_out[static_cast<uint32_t>(size)], 0, paddingSize);
    }

    return 0;
}

int main()
{
    vector<char> fileData;
    size_t fileSize;
    //path fileName("D:/temp/upx/Autoruns64.upx.exe");
    //path fileName("D:/temp/upx/AccessEnum.upx.exe");
    //path fileName("D:/Work/DFI/UPXSamples/toobig32.upx.exe");
    //path fileName("D:/Work/DFI/UPXSamples/toobig64.upx.exe");
    //path fileName("D:/Work/DFI/DFISamples/Problem/Black_84274470dd69d3fb2f4e86c822910b8dfbabd0d815f3eaecac0d759aa647beac");
    path fileName("D:/Work/DFI/DFISamples/Problem/White_9129b9869a7b6d35be105f13a61aa47243ee12bb7ddd056bf0efdf55b81e42e5");
    int res = read_entire_file(fileName, fileData, fileSize);
    if (0 != res) {
        printf("Failed to read input file %s", fileName.string().c_str());
        return res;
    }
    //InMemoryFile inputFile(reinterpret_cast<uintptr_t>(fileData.data()), fileSize);
    //unique_ptr<InMemoryUnpackW64Pe> unpacker64 = make_unique<InMemoryUnpackW64Pe>(static_cast<InputFile *>(&inputFile));
    //unique_ptr<InMemoryUnpackW32Pe> unpacker32 = make_unique<InMemoryUnpackW32Pe>(static_cast<InputFile *>(&inputFile));
    //InMemoryOutputFile outputFile(fileSize * 10);
    //try
    //{
    //    if (unpacker64->canUnpack()) {
    //        unpacker64->unpack(&outputFile);
    //    }
    //    else if (unpacker32->canUnpack()) {
    //        unpacker32->unpack(&outputFile);
    //    }
    //}
    //catch (IOException & e)
    //{
    //    printf("Error: %s\n", e.getMsg());
    //}
    upxlib upx;
    auto outputData = upx.tryToUnpack(reinterpret_cast<uintptr_t>(fileData.data()),
                                      fileData.size());
    if ((nullptr != outputData.first) && (0 < outputData.second)) {
        ofstream dumpFile("C:/temp/unpack.exe", ios::binary | ios::out);
        dumpFile.write(reinterpret_cast<const char *>(outputData.first),
                       outputData.second);
    }
    return 0;
}

