#include <memory>

#include "conf.h"
#include "file.h"
#include "filter.h"
#include "packer.h"
#include "pefile.h"
#include "linker.h"

#include "InMemoryUnpackW32Pe.h"

using namespace std;

int InMemoryUnpackW32Pe::canUnpack()
{
    if (getFormat() <= 0) {
        return 0;
    }
    if (255 <= getFormat()) {
        return 0;
    }
    if (getVersion() < 11) {
        return 0;
    }
    if (14 < getVersion()) {
        return 0;
    }
    if (15 < strlen(getName())) {
        return 0;
    }
    if (32 < strlen(getFullName(opt))) {
        return 0;
    }
    if (32 < strlen(getFullName(NULL))) {
        return 0;
    }
    if (nullptr == bele) {
        return 0;
    }
    if (getFormat() != UPX_F_MACH_FAT) // macho/fat is multiarch
    {
        const N_BELE_RTP::AbstractPolicy *format_bele;
        if (getFormat() < 128) {
            format_bele = &N_BELE_RTP::le_policy;
        }
        else {
            format_bele = &N_BELE_RTP::be_policy;
        }
        if (bele != format_bele) {
            return 0;
        }
    }
    {
        auto l = make_unique<Linker>();
        if (bele != l->bele) {
            return 0;
        }
    }

    try {
        initPackHeader();
        PackW32Pe::canUnpack();
        updatePackHeader();
        fi->seek(0, SEEK_SET);
        if (0 == PackW32Pe::canUnpack()) {
            return 0;
        }
        fi->seek(0, SEEK_SET);
    }
    catch (const IOException &) {
        return 0;
    }
    catch (...) {
        return 0;
    }
    if ((0 == ph.c_len) || (0 == ph.u_len)) {
        return 0;
    }

    return 1;

}

void InMemoryUnpackW32Pe::unpack(UPXOutputFile *fo)
{
    PackW32Pe::unpack(fo);
}
