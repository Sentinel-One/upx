#pragma once

#include <stdexcept>
#include <memory>
#include <stdint.h>
#include "file.h"

class InMemoryFile : public UPXInputFile
{
public:
    InMemoryFile(uintptr_t ptr, off_t length) : _ptr(ptr)
    {
        _length = length;
    };
    virtual ~InMemoryFile() = default;

    void sopen(const char *, int, int) override {};
    void open(const char *, int) override {}

    int read(void * buf, int len) override;
    int readx(void * buf, int len) override;
    int read(MemBuffer * buf, int len) override;
    int readx(MemBuffer * buf, int len) override;
    int read(MemBuffer & buf, int len) override;
    int readx(MemBuffer & buf, int len) override;

    virtual off_t seek(upx_int64_t off, int whence);
    virtual off_t tell() const;
    virtual off_t st_size_orig() const;
protected:
    uintptr_t _ptr;
};

class InMemoryOutputFile : public UPXOutputFile
{
public:
    InMemoryOutputFile(off_t maximumSize);
    virtual ~InMemoryOutputFile() = default;

    virtual void sopen(const char *, int, int, int)
    {
        throw std::runtime_error("In memory file does not support sopen");
    }
    virtual void open(const char * name, int flags, int mode)
    {
        sopen(name, flags, -1, mode);
    }
    virtual bool openStdout(int flags = 0, bool force = false)
    {
        throw std::runtime_error("In memory file does not support stdout");
    }

    virtual void write(const void * buf, int len) override;
    virtual void write(const MemBuffer * buf, int len) override;
    virtual void write(const MemBuffer & buf, int len) override;
    virtual void set_extent(off_t offset, off_t length) override;
    virtual off_t unset_extent() override;
    virtual void reset();

    virtual off_t seek(upx_int64_t off, int whence) override;
    virtual void rewrite(const void * buf, int len) override;
    uint8_t * getInternalBuffer()
    {
        return _buffer.get();
    }
protected:
    off_t _max_length;
    std::unique_ptr<uint8_t[]> _buffer;
};
