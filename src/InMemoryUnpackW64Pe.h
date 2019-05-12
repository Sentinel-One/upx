#pragma once

#include "p_w64pep.h"

class InMemoryUnpackW64Pe : public PackW64Pep
{

public:
    InMemoryUnpackW64Pe(UPXInputFile *f) : PackW64Pep(f) {}
    virtual ~InMemoryUnpackW64Pe() = default;
    virtual int canUnpack() override;
    // Making the method public
    virtual void unpack(UPXOutputFile *fo) override;
};
