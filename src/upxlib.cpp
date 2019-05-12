#ifdef _MSC_BUILD
#include <windows.h>
#include <filesystem>
#else
#include <dirent.h>
#include <experimental/filesystem>
#endif

#include "conf.h"
#include "packer.h"
#include "pefile.h"
#include "InMemoryUnpackW64Pe.h"
#include "InMemoryUnpackW32Pe.h"
#include "InMemoryFile.h"

#include <utility>
#include <stdint.h>
#include <vector>
#include <fstream>
#include <cstring>
#include <memory>

#include "upxlib.h"

const char * progname = "upxlib";

void options_t::reset()
{
    options_t * o = this;
    memset(o, 0, sizeof(*o));
    o->crp.reset();

    o->cmd = CMD_COMPRESS;
    o->method = M_NONE;
    o->level = -1;
    o->filter = FT_NONE;

    o->backup = -1;
    o->overlay = COPY_OVERLAY;
    o->preserve_mode = true;
    o->preserve_ownership = true;
    o->preserve_timestamp = true;

    o->console = CON_FILE;
#if (ACC_OS_DOS32) && defined(__DJGPP__)
    o->console = CON_INIT;
#elif (USE_SCREEN_WIN32)
    o->console = CON_INIT;
#elif 1 && defined(__linux__)
    o->console = CON_INIT;
#endif
    o->verbose = 2;

    o->win32_pe.compress_exports = 1;
    o->win32_pe.compress_icons = 2;
    o->win32_pe.compress_resources = -1;
    for (unsigned i = 0; i < TABLESIZE(o->win32_pe.compress_rt); i++) {
        o->win32_pe.compress_rt[i] = -1;
    }
    o->win32_pe.compress_rt[24] = false;    // 24 == RT_MANIFEST
    o->win32_pe.strip_relocs = -1;
    o->win32_pe.keep_resource = "";
}

static options_t global_options;
options_t * opt = &global_options;

upxlib::upxlib()
{
    if (CMD_NONE == global_options.cmd) {
        global_options.reset();
    }
}

upxlib::~upxlib() = default;

std::pair<const uint8_t *, uint32_t> upxlib::tryToUnpack(uintptr_t data,
        uint32_t length)
{
    if (!outputBuffer) {
        outputBuffer = std::make_unique<InMemoryOutputFile>(100 * 1024 * 1024);
    }
    InMemoryFile inputFile(data, length);
    try {
        bool unpackOk = false;
        auto unpacker64 = std::make_unique<InMemoryUnpackW64Pe>
                          (static_cast<UPXInputFile *>(&inputFile));
        if (unpacker64->canUnpack()) {
            unpacker64->unpack(outputBuffer.get());
            if (0 < outputBuffer->getBytesWritten()) {
                unpackOk = true;
            }
        } else {
            auto unpacker32 = std::make_unique<InMemoryUnpackW32Pe>
                              (static_cast<UPXInputFile *>(&inputFile));
            if (unpacker32->canUnpack()) {
                unpacker32->unpack(outputBuffer.get());
                if (0 < outputBuffer->getBytesWritten()) {
                    unpackOk = true;
                }
            }
        }
        if (unpackOk) {
            return std::make_pair<const uint8_t *, uint32_t>
                   (outputBuffer->getInternalBuffer(), outputBuffer->getBytesWritten());
        }
    } catch (Exception &) {
    }

    return std::make_pair<const uint8_t *, uint32_t>(nullptr, 0);
}


static int pr_need_nl = 0;


void printSetNl(int need_nl)
{
    pr_need_nl = need_nl;
}

void printClearLine(FILE *)
{
    return;
}


void printErr(const char *, const Throwable *)
{
    return;
}


void __acc_cdecl_va printErr(const char *, const char *, ...)
{
    return;
}


void __acc_cdecl_va printWarn(const char *, const char *, ...)
{
    return;
}


void printUnhandledException(const char *, const std::exception *)
{
    return;
}

static int info_header = 0;

void infoHeader()
{
    info_header = 0;
}

void infoHeader(const char *, ...)
{
    return;
}


void info(const char *, ...)
{
    return;
}


void infoWarning(const char *, ...)
{
    return;
}


void infoWriting(const char *, long)
{
    return;
}
