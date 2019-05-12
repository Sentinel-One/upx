#pragma once

#include "p_w32pe.h"

class InMemoryUnpackW32Pe : public PackW32Pe
{

public:
    InMemoryUnpackW32Pe(UPXInputFile *f) : PackW32Pe(f) {}
    virtual ~InMemoryUnpackW32Pe() = default;
    virtual int canUnpack() override;
    // Making the method public
    void unpack(UPXOutputFile *fo) override;
};
