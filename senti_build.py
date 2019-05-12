#!/usr/bin/env python
from __future__ import print_function
import baker
import colorama
import colors
import functools
import jinja2
import os
import platform
import shutil
import subprocess
import sys
import time
from copy import copy, deepcopy
from zipfile import ZipFile, ZIP_DEFLATED
from glob import glob

def cache(func):
    saved = {}
    @functools.wraps(func)
    def newfunc(*args):
        argsHashable = '!'.join([repr(x) for x in args])
        if argsHashable in saved:
            return deepcopy(saved[argsHashable])
        result = func(*args)
        saved[argsHashable] = result
        return result
    return newfunc

def logger(func):
    def _logger(*args, **kwargs):
        output = "--- "
        output += func.__name__
        if args != ():
            output += " "
            output += repr(args)
        if kwargs != {}:
            output += " "
            output += repr(kwargs)
        output += " ---"
        print(colors.yellow(output))
        result = func(*args, **kwargs)
        output = "+++ "
        if isinstance(result, list):
            output += '\n'
            for x in result:
                output += repr(x)
                output += "\n"
        elif isinstance(result, dict):
            output += '\n'
            for k, v in result.items():
                output += repr(k)
                output += ": "
                output += repr(v)
                output += "\n"
        else:
            output += repr(result)
        output += " +++"
        if None != result:
            print(colors.yellow(output))
        return result
    return _logger

def printAndExecute(commandLine, cwd=None, env=None, redirect=False, checkResult=True):
    if not env:
        env = os.environ
    if isinstance(commandLine, list):
        commandLine = ' '.join(commandLine).strip()
    print(colors.blue(commandLine))
    if redirect:
        process = subprocess.Popen(commandLine, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if checkResult and process.returncode:
            raise subprocess.CalledProcessError(process.returncode, commandLine, output=stderr)
        return (process.returncode, stdout, stderr)
    else:
        if checkResult:
            executionProc = subprocess.check_call
        else:
            executionProc = subprocess.call
        return executionProc(commandLine, shell=True, cwd=cwd, env=env)

def write_if_changed(file_name, data):
    if not os.path.isfile(file_name):
        print(colors.yellow("Creating file %s" % file_name))
        data_changed = True
    else:
        with file(file_name, 'rb') as f:
            old_data = f.read()
        if old_data != data:
            print(colors.yellow("Updating file %s" % file_name))
            data_changed = True
        else:
            data_changed = False

    if not data_changed:
        return

    with file(file_name, 'wb') as f:
        f.write(data)

@cache
@logger
@baker.command
def get_current_upx_zip(dfi_path):
    current_upx_zip = glob(os.path.join(dfi_path, 'externals_tracked', 'upx_*.zip'))
    if not current_upx_zip:
        raise Exception("No upx zip")
    if 1 < len(current_upx_zip):
        raise Exception("Too many UPX zips %r" % current_upx_zip)
    return current_upx_zip[0]

@logger
@baker.command
def get_build_number(dfi_path):
    current_upx_zip = os.path.basename(get_current_upx_zip(dfi_path))
    _, version = current_upx_zip.split('_')
    version = version[:version.rfind('.')]
    version = [int(x) for x in version.split('.')]
    current_build = version[-1]
    version = version[:-1]
    return current_build + 1

@logger
@baker.command
def get_version_from_news():
    news = open('NEWS', 'rb').readlines()
    for l in news:
        if 'Changes in ' in l:
            l = l[len('Changes in '):]
            version = l[:l.find(' ')]
            version = [int(x) for x in version.split('.')]
            break
    else:
        raise Exception("Didn't find version in NEWS file, they probebly changes the format of the file")
    return version

@logger
@baker.command
def get_vsdev_path():
    VS_PROMPT_COMMANDS = 'pushd . & "%s" & popd'
    VS_WHERE = os.path.expandvars("%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe")
    if not os.path.isfile(VS_WHERE):
        VS_WHERE = os.path.expandvars("%ProgramFiles%\\Microsoft Visual Studio\\Installer\\vswhere.exe")
        if not os.path.isfile(VS_WHERE):
            # VS2017 not installed
            VS_PROMPT = os.path.expandvars("%ProgramFiles(x86)%\\Microsoft Visual Studio 14.0\Common7\Tools\VsDevCmd.bat")
            if not os.path.isfile(VS_PROMPT):
                VS_PROMPT = os.path.expandvars("%ProgramFiles%\\Microsoft Visual Studio 14.0\Common7\Tools\VsDevCmd.bat")
                if not os.path.isfile(VS_PROMPT):
                    raise Exception("MS Visual Studio not found")
            return VS_PROMPT_COMMANDS % VS_PROMPT

    VS_PROMPT = os.path.join(subprocess.check_output([
             VS_WHERE,
             "-products",
             "*",
             "-latest",
             "-requires",
             "Microsoft.Component.MSBuild",
             "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
             "-property",
             "installationPath"]).rstrip(), "Common7\\Tools\\VsDevCmd.bat")
    # VsDevCmd.bat changes the current working directory.
    if len(VS_PROMPT) == 0:
        raise Exception("A Visual Studio installation with the required components was not found.")
    return VS_PROMPT_COMMANDS % VS_PROMPT

@logger
@baker.command
def build(arch="x64", configuration="Release"):
    VS_PROMPT = get_vsdev_path()
    commandLine = [
            '%s & msbuild win32build\\upx.sln' % VS_PROMPT,
            '/clp:ShowCommandLine;EnableMPLogging',
            '/p:Configuration=%s' % configuration,
            '/p:Platform=%s' % arch,
            '/consoleloggerparameters:EnableMPLogging;ForceNoAlign;ForceConsoleColor',
            '/maxcpucount',
            '/nodeReuse:False' ]
    printAndExecute(commandLine)

@logger
@baker.command
def make_package(dfi_path):
    remove_unnessery_files_for_package()
    version = get_version_from_news()
    version.append(get_build_number(dfi_path))
    output_file = os.path.join(dfi_path, 'externals_tracked', 'upx_%s.zip' % ('.'.join([str(x) for x in version])))
    with ZipFile(output_file, "w", ZIP_DEFLATED) as zipFile:
        for root, firnames, filenames in os.walk('.'):
            if '.git' in root:
                continue
            for fname in filenames:
                target = os.path.join(root, fname)
                print("Writing %s" % target)
                zipFile.write(target, 'upx/' + target)

@logger
@baker.command
def patch_source():
    data = open('src\\compress_lzma.cpp', 'rb').read()
    data = safe_replace(data, '#undef _WIN32\n', '//undef _WIN32\n')
    data = safe_replace(data, '#undef _WIN32_WCE\n', '//undef _WIN32_WCE\n')
    open('src\\compress_lzma.cpp', 'wb').write(data)
    data = open('src\\conf.h', 'rb').read()
    pos = data.find('#define __UPX_CONF_H 1\n')
    assert(-1 != pos)
    pos += len('#define __UPX_CONF_H 1\n')
    data = data[:pos] + '''
    #ifdef _MSC_BUILD
    #include <windows.h>
    #endif
    ''' + data[pos:]
    data = safe_replace(data, '''#if (ACC_OS_CYGWIN || ACC_OS_DOS16 || ACC_OS_DOS32 || ACC_OS_EMX || ACC_OS_OS2 || ACC_OS_OS216 || ACC_OS_WIN16 || ACC_OS_WIN32 || ACC_OS_WIN64)
#  if defined(INVALID_HANDLE_VALUE) || defined(MAKEWORD) || defined(RT_CURSOR)
#    error "something pulled in <windows.h>"
#  endif
#endif''', '')
    open('src\\conf.h' ,'wb').write(data)
    data = open('src\\console.h', 'rb').read()
    pos = data.find('''#if 0 || (NO_SCREEN)
#  undef USE_SCREEN''')
    assert(-1 != pos)
    pos += len('''#if 0 || (NO_SCREEN)
#  undef USE_SCREEN''')
    if '#undef USE_SCREEN_WIN32' not in data:
        data = data[:pos] + '''
        #ifdef USE_SCREEN_WIN32
        #undef USE_SCREEN_WIN32
        #endif
        ''' + data[pos:]
    open('src\\console.h', 'wb').write(data)
    data = open('src\\pefile.h', 'rb').read()
    data = safe_replace(data, 'IMAGE_DLL_CHARACTERISTICS_DYNAMIC_BASE         = 0x0040,' ,'IMAGE_DLL_CHARACTERISTICS_DYNAMIC_BASE         = 0x0040')
    data = safe_replace(data, 'IMAGE_DLL_CHARACTERISTICS_FORCE_INTEGRITY      = 0x0080,', '')
    data = safe_replace(data, 'IMAGE_DLL_CHARACTERISTICS_NX_COMPAT            = 0x0100,', '')
    data = safe_replace(data, 'IMAGE_DLLCHARACTERISTICS_NO_ISOLATION          = 0x0200,', '')
    data = safe_replace(data, 'IMAGE_DLLCHARACTERISTICS_NO_SEH                = 0x0400,', '')
    data = safe_replace(data, 'IMAGE_DLLCHARACTERISTICS_NO_BIND               = 0x0800,', '')
    data = safe_replace(data, 'IMAGE_DLLCHARACTERISTICS_WDM_DRIVER            = 0x2000,', '')
    data = safe_replace(data, 'IMAGE_DLLCHARACTERISTICS_TERMINAL_SERVER_AWARE = 0x8000', '')
    open('src\\pefile.h', 'wb').write(data)
    data = open('src\\snprintf.cpp', 'rb').read()
    data = safe_replace(data, 'size_t len = strlen(s);', 'size_t len = strlen((const char *)(s));')
    data = safe_replace(data, 'upx_rsize_t upx_strlen(const char *s) {', 'upx_rsize_t upx_strlen(const upx_byte *s) {')
    open('src\\snprintf.cpp', 'wb').write(data)
    data = open('src\\snprintf.h', 'rb').read()
    data = safe_replace(data, 'upx_rsize_t upx_strlen(const char *);', 'upx_rsize_t upx_strlen(const upx_byte *s);')
    data = safe_replace(data, '#undef sprintf', '')
    data = safe_replace(data, '#define sprintf error_sprintf_is_dangerous_use_snprintf', '')
    data = safe_replace(data, '#undef strlen', '')
    data = safe_replace(data, '#define strlen upx_strlen', '')
    open('src\\snprintf.h', 'wb').write(data)
    data = open('Makefile', 'rb').read()
    data = safe_replace(data, '\$(MAKE) -C doc $@', '')
    open('Makefile', 'wb').write(data)
    data = open('src\\Makefile', 'rb').read()
    src_list, _ = get_project_files('linux')
    makefile_src_list = '\n'
    for fname in src_list:
        makefile_src_list += '    src/%s \\\n' % fname
    data = safe_replace(data, 'upx_SOURCES := $(sort $(wildcard $(srcdir)/*.cpp))', 'upx_SOURCES := \\%s\n' % makefile_src_list)
    data = safe_replace(data, '\t$(CHECK_WHITESPACE)\n', '\tar rs -o upxlib.a $(upx_OBJECTS)\n')
    data = safe_replace(data, '%.o : %.cpp | ./.depend', '%.o : %.cpp')
    data = safe_replace(data, './.depend compress_lzma$(objext) : INCLUDES += -I$(UPX_LZMADIR)', 'INCLUDES += -I$(UPX_LZMADIR)')
    data = safe_replace(data, 'LIBS += ../../zlib/libz.a \\', 'LIBS += -lucl -lz')
    data = safe_replace(data, '../../xz/src/liblzma/.libs/liblzma.a \\' ,'')
    data = safe_replace(data, '../../ucl/src/.libs/libucl.a', '')
    open('src\\Makefile', 'wb').write(data)
    data = open('src\\compress_ucl.cpp', 'rb').read()
    data = safe_replace(data, '#if 1 && (UCL_USE_ASM)', '#if 0 && (UCL_USE_ASM)')
    open('src\\compress_ucl.cpp', 'wb').write(data)

def delete_if_exists(fname):
    if os.path.isfile(fname):
        print("Removing: " + colors.yellow(fname))
        os.remove(fname)
    if os.path.isdir(fname):
        print("Removing dir: " + colors.yellow(fname))
        try:
            shutil.rmtree(fname)
        except:
            print(colors.red("Failed to remove: " + fname))

@logger
@baker.command
def remove_unnessery_files_for_package():
    delete_if_exists('lib\\Release\\x64\\upx.lib')
    delete_if_exists('lib\\Debug\\x64\\upx.lib')
    delete_if_exists('lib\\Release\\Win32\\upx.lib')
    delete_if_exists('lib\\Debug\\Win32\\upx.lib')
    delete_if_exists('bin\\Debug')
    delete_if_exists('bin\\Release\\Win32')
    delete_if_exists('bin\\Release\\x64\\testlib.exe')
    delete_if_exists('bin\\Release\\x64\\testlib.pdb')
    delete_if_exists('bin\\Release\\x64\\upxconsole.pdb')
    delete_if_exists('win32build\\output')
    delete_if_exists('win32build\\.vs')

@logger
@baker.command
def clean():
    delete_if_exists('lib')
    delete_if_exists('bin')
    delete_if_exists('win32build\\output')

def load_original_prop(dfi_path, prop_name):
    return open(os.path.join(dfi_path, 'windows', 'props', prop_name), 'rb').read()

def safe_replace(data, src, dst, multi=False):
    count = data.count(src)
    count_target = data.count(dst)
    if 0 == count and 0 == count_target:
        raise Exception("Pattern not found")
    if 1 < count and not multi:
        raise Exception("Multi match!")
    return data.replace(src, dst)

@logger
@baker.command
def write_props(dfi_path):
    if not os.path.isdir('win32build'):
        os.mkdir('win32build')
    sentinel_props = load_original_prop(dfi_path, 'sentinel.props')
    sentinel_props = safe_replace(sentinel_props, '<TreatWarningAsError>true</TreatWarningAsError>', '<TreatWarningAsError>false</TreatWarningAsError>')
    sentinel_props = safe_replace(sentinel_props, '<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>', '<DebugInformationFormat>OldStyle</DebugInformationFormat>')
    sentinel_props = safe_replace(sentinel_props, '<CompileAs>CompileAsCpp</CompileAs>', '')
    sentinel_props = safe_replace(sentinel_props, '<PreprocessorDefinitions>NOMINMAX;', '<PreprocessorDefinitions>_WIN32;NORESOURCE;_UNICODE;UNICODE;_CRT_SECURE_NO_WARNINGS;_HAS_AUTO_PTR_ETC=1;NO_SCREEN;NOMINMAX;')
    pos = sentinel_props.find('<ItemDefinitionGroup Label="GlobalConfigurations">')
    assert(-1 != pos)
    pos = sentinel_props.find('<Link>', pos)
    assert(-1 != pos)
    endPos = sentinel_props.find('</Link>', pos)
    assert(-1 != endPos)
    sentinel_props = sentinel_props[:pos] + '''
    <Link>
      <GenerateDebugInformation>true</GenerateDebugInformation>
      <AdditionalOptions>/ignore:4221 %(AdditionalOptions)</AdditionalOptions>
    </Link>
    <Lib>
      <AdditionalOptions>/ignore:4221 %(AdditionalOptions)</AdditionalOptions>
    </Lib>''' + sentinel_props[endPos+len('</Link>'):]
    open('win32build\\sentinel.props', 'wb').write(sentinel_props)
    binary_props = load_original_prop(dfi_path, 'binary.props')
    binary_props = safe_replace(binary_props,
        '<OutDir>$(SolutionDir)output\\bin\$(Configuration)\$(Platform)\</OutDir>',
        '<OutDir>$(SolutionDir)..\\bin\$(Configuration)\$(Platform)\</OutDir>')
    open('win32build\\binary.props', 'wb').write(binary_props)
    library_props = load_original_prop(dfi_path, 'library.props')
    library_props = safe_replace(library_props,
        '<OutDir>$(SolutionDir)output\lib\$(Configuration)\$(Platform)\</OutDir>',
        '<OutDir>$(SolutionDir)..\lib\$(Configuration)\$(Platform)\</OutDir>')
    pos = library_props.find('<ItemDefinitionGroup >')
    assert(-1 != pos)
    pos += len('<ItemDefinitionGroup >') + 1
    library_props = library_props[:pos] + '''
        <ProjectReference>
          <LinkLibraryDependencies>false</LinkLibraryDependencies>
        </ProjectReference>
        ''' + library_props[pos:]
    open('win32build\\library.props', 'wb').write(library_props)
    lzma_props = load_original_prop(dfi_path, 'lzma.props')
    lzma_props = safe_replace(lzma_props, '$(SolutionDir)..\\externals\\xz', '$(SolutionDir)..\\..\\xz', True)
    open('win32build\\lzma.props', 'wb').write(lzma_props)
    lzma_props = load_original_prop(dfi_path, 'lzma.props')
    lzma_props = safe_replace(lzma_props, '$(SolutionDir)..\\externals\\xz\\src\\liblzma\\api', '$(SolutionDir)..\\src\\lzma-sdk', True)
    pos = lzma_props.find('<Link>')
    assert(-1 != pos)
    endPos = lzma_props.find('</Link>')
    assert(-1 != endPos)
    lzma_props = lzma_props[:pos] + lzma_props[endPos+len('</Link>')+1:]
    pos = lzma_props.find('<Lib>')
    assert(-1 != pos)
    endPos = lzma_props.find('</Lib>')
    assert(-1 != endPos)
    lzma_props = lzma_props[:pos] + lzma_props[endPos+len('</Lib>')+1:]
    open('win32build\\lzma-c.props', 'wb').write(lzma_props)
    ucl_props = load_original_prop(dfi_path, 'ucl.props')
    ucl_props = safe_replace(ucl_props, '$(SolutionDir)..\\externals\\ucl', '$(SolutionDir)..\\..\\ucl', True)
    open('win32build\\ucl.props', 'wb').write(ucl_props)
    zlib_props = load_original_prop(dfi_path, 'zlib.props')
    zlib_props = safe_replace(zlib_props, '$(SolutionDir)..\\externals\\zlib', '$(SolutionDir)..\\..\\zlib', True)
    zlib_props = safe_replace(zlib_props, '<PreprocessorDefinitions>ZLIB_WINAPI;%(PreprocessorDefinitions)</PreprocessorDefinitions>', '<!-- PreprocessorDefinitions>ZLIB_WINAPI;%(PreprocessorDefinitions)</PreprocessorDefinitions -->')
    open('win32build\\zlib.props', 'wb').write(zlib_props)
    shutil.copyfile(
        os.path.join(dfi_path, 'windows', 'props', 'console.props'),
        'win32build\\console.props')
    shutil.copyfile(
        os.path.join(dfi_path, 'windows', 'props', 'sdk.props'),
        'win32build\\sdk.props')
    shutil.copyfile(
        os.path.join(dfi_path, 'windows', 'props', 'userLand.props'),
        'win32build\\userLand.props')
    open('win32build\\upxlib.props', 'wb').write('''
<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ImportGroup Label="PropertySheets" />
  <ItemDefinitionGroup>
    <ClCompile>
      <AdditionalIncludeDirectories>%(AdditionalIncludeDirectories);$(SolutionDir)..\src</AdditionalIncludeDirectories>
    </ClCompile>
    <Link>
      <AdditionalDependencies>$(SolutionDir)..\lib\$(Configuration)\$(Platform)\upxlib.lib;%(AdditionalDependencies)</AdditionalDependencies>
    </Link>
    <Lib>
      <AdditionalDependencies>$(SolutionDir)..\lib\$(Configuration)\$(Platform)\upxlib.lib;%(AdditionalDependencies)</AdditionalDependencies>
    </Lib>
  </ItemDefinitionGroup>
</Project>''')


def init_jinja_template(template_file):
    dirname = os.path.dirname(template_file)
    templateLoader = jinja2.FileSystemLoader(searchpath=dirname)
    templateEnvironment = jinja2.Environment(loader=templateLoader, extensions=["jinja2.ext.do"])
    return templateEnvironment.get_template(os.path.basename(template_file))

def render(input_data, template_filename):
    template = init_jinja_template(template_filename)
    return template.render(**input_data)

PROJ_GUID = {
        'upx' : '{C13912EF-103E-4980-BD39-FFDB5F8E7535}',
        'upxlib' : '{7124AA41-F360-4266-9FB2-C5811135A021}',
        'upxconsole' : '{CEE19A1C-2195-4DE3-AC64-F7F2E1C5C788}' }

def get_project_files(proj_name):
    header_files = [os.path.basename(x) for x in glob('src\\*.h')]
    src_files    = [os.path.basename(x) for x in glob('src\\*.cpp')]
    if 'upx' == proj_name:
        header_files = [x for x in header_files if x not in [
            'InMemoryFile.h',
            'InMemoryUnpackW32Pe.h',
            'InMemoryUnpackW64Pe.h',
            'p_vmlinx.h',
            'p_vmlinz.h',
            's_djgpp2.h',
            's_vcsa.h',
            'stdcxx.h',
            'upxlib.h']]
        src_files = [x for x in src_files if x not in [
            'InMemoryFile.cpp',
            'InMemoryUnpackW32Pe.cpp',
            'InMemoryUnpackW64Pe.cpp',
            'main.cpp',
            'p_vmlinx.cpp',
            'p_vmlinz.cpp',
            's_djgpp2.cpp',
            's_vcsa.cpp',
            'stdcxx.cpp',
            'testlib.cpp',
            'upxlib.cpp']]
    elif 'upxlib' == proj_name:
        header_files = [x for x in header_files if x not in [
            'bele.h',
            'bele_policy.h',
            'bptr.h',
            'lefile.h',
            's_djgpp2.h',
            's_vcsa.h',
            'screen.h',
            'stdcxx.h',
            'version.h']]
        src_files = [x for x in src_files if x not in [
            'help.cpp',
            'lefile.cpp',
            'main.cpp',
            'msg.cpp',
            's_djgpp2.cpp',
            's_object.cpp',
            's_vcsa.cpp',
            's_win32.cpp',
            'stdcxx.cpp',
            'testlib.cpp',
            'work.cpp']]
    elif 'linux' == proj_name:
        src_files = [x for x in src_files if x not in [
            'help.cpp',
            'lefile.cpp',
            'main.cpp',
            'msg.cpp',
            's_djgpp2.cpp',
            's_object.cpp',
            's_vcsa.cpp',
            's_win32.cpp',
            'stdcxx.cpp',
            'testlib.cpp',
            'work.cpp']]
    elif 'upxconsole' == proj_name:
        header_files = [x for x in header_files if x not in [
            'InMemoryFile.h',
            'InMemoryUnpackW32Pe.h',
            'InMemoryUnpackW64Pe.h',
            'testlib.h',
            'upxlib.h']]
        src_files = [x for x in src_files if x not in [
            'InMemoryFile.cpp',
            'InMemoryUnpackW32Pe.cpp',
            'InMemoryUnpackW64Pe.cpp',
            'testlib.cpp',
            'upxlib.cpp']]
    else:
        raise Exception("Unsupported project %s" % proj_name)
    return src_files, header_files

@logger
@baker.command
def write_vcxproj(proj_name):
    if not os.path.isdir('win32build'):
        os.mkdir('win32build')
    src_files, header_files = get_project_files(proj_name)
    configuration_props = 'library.props'
    configuration_type = 'StaticLibrary'
    if proj_name == 'upxconsole':
        configuration_props = 'console.props'
        configuration_type = 'Application'

    addition_props = []
    if 'upxconsole' == proj_name or 'upx' == proj_name:
        addition_props = [ "ucl.props", "zlib.props", "lzma-c.props" ]

    with open('win32build\\%s.vcxproj' % proj_name, 'wb') as output:
        output.write(render({
            'header_files' : header_files,
            'src_files' : src_files,
            'configuration_type' : configuration_type,
            'configuration_props' : configuration_props,
            'proj_guid' : PROJ_GUID[proj_name],
            'proj_name' : proj_name,
            'addition_props' : addition_props}, 'senti_vcxproj.template'))

@logger
@baker.command
def write_vs_files():
    write_vcxproj('upx')
    write_vcxproj('upxlib')
    write_vcxproj('upxconsole')
    with open('win32build\\upx.sln', 'wb') as output:
        output.write(render({
            "solution_guid" : "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}",
            "projects" : PROJ_GUID.items()}, 'senti_sln.template'))


@logger
@baker.command
def build_all(dfi_path):
    if not os.path.isdir('..\\ucl'):
        raise Exception("Precompiled UCL is required at ..\\ucl")
    if not os.path.isdir('..\\zlib'):
        raise Exception("Precompiled zlib is required at ..\\zlib")
    for fname in [
            'InMemoryFile.cpp',
            'InMemoryFile.h',
            'InMemoryUnpackW32Pe.cpp',
            'InMemoryUnpackW32Pe.h',
            'InMemoryUnpackW64Pe.cpp',
            'InMemoryUnpackW64Pe.h',
            'testlib.cpp',
            'upxlib.cpp',
            'upxlib.h']:
        if not os.path.isfile(os.path.join('src', fname)):
            raise Exception("Please copy file %s to src\\%s" % (fname, fname))
    write_vs_files()
    patch_source()
    write_props(dfi_path)
    clean()
    build(arch="x64", configuration="Release")
    build(arch="x64", configuration="Debug")
    build(arch="x86", configuration="Release")
    build(arch="x86", configuration="Debug")
    remove_unnessery_files_for_package()
    current_package = get_current_upx_zip(dfi_path)
    make_package(dfi_path)
    os.unlink(current_package)
    delete_if_exists(current_package)


if __name__ == '__main__':
    if platform.system() != "Windows":
        raise Exception("This script is made for Windows VS builds only")
    colorama.init(strip=False)
    baker.run()
