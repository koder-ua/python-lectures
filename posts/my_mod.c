#include <cstdio>

/* 
EXT_BUILD

#set ADD_SOURCE_FILES=
#set ADD_LIBS=
#set INCLUDE_DIRS=
#set LIB_DIRS=
#set COMPILER_FLAGS=

#build_commands:
#    g++ -shared -fPIC {source_files} -o {so_name}

export int add(int, int)
export int sub(int, int)

END_EXT_BUILD
*/

extern "C" int add(int x, int y)
{
	return x + y;	
}

extern "C" int sub(int x, int y)
{
	return x - y;	
}

