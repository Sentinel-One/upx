#ifdef _MSC_BUILD
#include <windows.h>
#include <intrin.h>
#else
#include <dirent.h>
#endif

#include <cstring>
#include <sys/types.h>

#include "conf.h"
#include "mem.h"
#include "except.h"
#include "InMemoryFile.h"

int InMemoryFile::read(void * buf, int len)
{
    if (_offset + len < _offset) {
        throw IOException("Negative length", 1);
    }
    if (nullptr == buf) {
        throw InternalError("Invalid buffer");
    }
    int bytesToRead = len;
    if (_length <= (_offset + len)) {
        bytesToRead = _length - _offset;
    }
    if (0 < bytesToRead) {
        std::memcpy(buf, reinterpret_cast<const void *>(_ptr + _offset), bytesToRead);
        _offset += bytesToRead;
    }
    if (bytesToRead < len) {
        std::memset(
            reinterpret_cast<void *>(static_cast<char *>(buf) + bytesToRead),
            0,
            len - bytesToRead);
    }
    return bytesToRead;
}

int InMemoryFile::readx(void * buf, int len)
{
    int l = this->read(buf, len);
    if (l != len) {
        throw EOFException("premature end of file", len - l);
    }
    return l;
}


int InMemoryFile::read(MemBuffer * buf, int len)
{
    buf->checkState();
    if (buf->getSize() < (unsigned)len) {
        throw InternalError("Buffer too small (0)");
    }
    return read(buf->getVoidPtr(), len);
}

int InMemoryFile::readx(MemBuffer * buf, int len)
{
    buf->checkState();
    if (buf->getSize() < (unsigned)len) {
        throw InternalError("Buffer too small (1)");
    }
    return readx(buf->getVoidPtr(), len);
}


int InMemoryFile::read(MemBuffer & buf, int len)
{
    if (buf.getSize() < (unsigned)len) {
        throw InternalError("Buffer too small (2)");
    }
    return read(&buf, len);
}

int InMemoryFile::readx(MemBuffer & buf, int len)
{
    if (buf.getSize() < (unsigned)len) {
        throw InternalError("Buffer too small (3)");
    }
    return readx(&buf, len);
}

off_t InMemoryFile::seek(upx_int64_t off64, int whence)
{
    off_t absOffset = 0;
    switch (whence) {
    case SEEK_SET:
        absOffset = static_cast<uint32_t>(off64);
        break;
    case SEEK_CUR:
        absOffset = static_cast<uint32_t>(off64 + _offset);
        break;
    case SEEK_END:
        absOffset = static_cast<uint32_t>(_length + off64);
        break;
    default:
        throw InternalError("Invalid seek");
    }
    if (_length < absOffset) {
        throw IOException("Bad seek (0)");
    }

    _offset = absOffset;
    return absOffset;
}


off_t InMemoryFile::tell() const
{
    return static_cast<off_t>(_offset);
}

off_t InMemoryFile::st_size_orig() const
{
    return static_cast<off_t>(_length);
}

InMemoryOutputFile::InMemoryOutputFile(off_t maximumSize) :
    _max_length(maximumSize)
{
    _buffer = std::make_unique<uint8_t[]>(maximumSize);
}

void InMemoryOutputFile::write(const void * buf, int len)
{
    if (len < 0) {
        throwIOException("bad write");
    }
    if (_max_length <= (_offset + len)) {
        throwIOException("Out of space");
    }
    memcpy(_buffer.get() + _offset, buf, len);
    _offset += len;
    bytes_written += len;
}

void InMemoryOutputFile::write(const MemBuffer * buf, int len)
{
    buf->checkState();
    if (buf->getSize() <= (unsigned)len) {
        throwIOException("Input buffer is smaller than length");
    }
    write(buf->getVoidPtr(), len);
}

void InMemoryOutputFile::write(const MemBuffer & buf, int len)
{
    write(&buf, len);
}

void InMemoryOutputFile::set_extent(off_t offset, off_t length)
{
    if ((_max_length < offset) || (offset < 0)) {
        throwIOException("Invalid offset");
    }
    if ((_max_length < length) || (offset < length)) {
        throwIOException("Invalid length");
    }
    _offset = offset;
    _length = length;
}

off_t InMemoryOutputFile::unset_extent()
{
    _offset = 0;
    return 0;
}

off_t InMemoryOutputFile::seek(upx_int64_t off64, int whence)
{
    off_t absOffset = 0;
    switch (whence) {
    case SEEK_SET:
        absOffset = off64;
        break;
    case SEEK_END:
        absOffset = _length - off64;
        break;
    case SEEK_CUR:
        absOffset = _offset + off64;
        break;
    }
    if (absOffset < 0) {
        throwIOException("Invalid seek (negative offset)");
    }
    if (_max_length <= absOffset) {
        throwIOException("Invalid seek (End of file)");
    }
    _offset = absOffset;
    return absOffset;
}

void InMemoryOutputFile::rewrite(const void * buf, int len)
{
    write(buf, len);
    bytes_written -= len;
}

void InMemoryOutputFile::reset()
{
    bytes_written = 0;
    _length = 0;
    _offset = 0;
}
