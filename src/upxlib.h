#pragma once

class InMemoryOutputFile;

class upxlib
{
public:
    upxlib();
    virtual ~upxlib();
    std::pair<const uint8_t *, uint32_t> tryToUnpack(uintptr_t data, uint32_t length);
protected:
    std::unique_ptr<InMemoryOutputFile> outputBuffer;
};
