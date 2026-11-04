cmake_minimum_required(VERSION 3.20)
set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")
if(NOT EXISTS "${PSXRECOMP_ROOT}/runtime/runtime.cmake")
    message(FATAL_ERROR
        "PSXRecomp runtime is missing: ${PSXRECOMP_ROOT}/runtime/runtime.cmake\n"
        "This project expects the psxrecomp framework checkout at ${PSXRECOMP_ROOT}.\n"
        "Run: git submodule update --init --recursive\n"
        "If psxrecomp/ is not a submodule, set -DPSXRECOMP_ROOT=<path-to-psxrecomp>.")
endif()

project(G_Police_Recompiled LANGUAGES C CXX)

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# Setup-host CI requires WIZARD_CMAKE_BLOCK / ENABLE_SETUP_WIZARD (FORCE_SETUP_HOST
# alone does not open first-run / Generate & rebuild).
set(PSX_RECOMP_UI ON CACHE BOOL "Shared launcher" FORCE)
set(PSX_DEBUG_TOOLS OFF CACHE BOOL "Production build")
set(PSX_STATIC_RUNTIME ON CACHE BOOL "Portable runtime" FORCE)
set(PSX_ENABLE_VULKAN ON CACHE BOOL "Vulkan renderer" FORCE)
set(PSX_NETPLAY OFF CACHE BOOL "Accepted offline release" FORCE)
set(PSX_SETUP_WIZARD ON CACHE BOOL "First-run setup" FORCE)
set(PSXRECOMP_BIOS_STEMS "SCPH5552" CACHE STRING "Accepted BIOS" FORCE)
set(PSXRECOMP_BIOS_STEM "SCPH5552" CACHE STRING "Accepted BIOS" FORCE)
set(PSXRECOMP_BIOS_PROFILE "${PSXRECOMP_ROOT}/bios/SCPH5552.toml" CACHE FILEPATH "Accepted BIOS" FORCE)
set(GPOLICE_GENERATED_STEM "generated/SLUS_005.44")
set(GPOLICE_GENERATED_DISPATCH "${GPOLICE_GENERATED_STEM}_dispatch.c")
set(GPOLICE_OVERLAY_STATIC "generated/overlays_static.c")
if(PSXRECOMP_FORCE_SETUP_HOST OR BPE_FORCE_SETUP_HOST
   OR NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${GPOLICE_GENERATED_DISPATCH}")
    set(PSXRECOMP_ALLOW_NO_BIOS ON CACHE BOOL
        "Allow first-run setup before BIOS code generation" FORCE)
endif()
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
set(PSXRECOMP_WINDOWS_MANIFEST
    "${CMAKE_CURRENT_SOURCE_DIR}/assets/windows/gpolice.manifest")

psxrecomp_add_game_runtime(psx-runtime


    ENABLE_SETUP_WIZARD
    EXE_NAME "G_Police_Recompiled"
    WINDOW_TITLE "G-Police Recompiled"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 1


    GEN_MARKER "${GPOLICE_GENERATED_DISPATCH}"
    GAME_OVERLAY_STATIC_C "${CMAKE_CURRENT_SOURCE_DIR}/${GPOLICE_OVERLAY_STATIC}"
    GEN_FULL_GLOB "${GPOLICE_GENERATED_STEM}_full_*.c"
    CODEGEN_SETUP_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/codegen_setup.c"
)

# GCC 16 WinLibs injects default-manifest.o even when the target supplies one.
if(MINGW AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    execute_process(
        COMMAND "${CMAKE_CXX_COMPILER}" -print-file-name=default-manifest.o
        RESULT_VARIABLE _gpolice_manifest_path_result
        OUTPUT_VARIABLE _gpolice_default_manifest
        ERROR_VARIABLE _gpolice_manifest_path_error
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _gpolice_manifest_path_result EQUAL 0)
        message(FATAL_ERROR
            "Unable to query the GNU default manifest: "
            "${_gpolice_manifest_path_error}")
    endif()

    if(EXISTS "${_gpolice_default_manifest}")
        execute_process(
            COMMAND "${CMAKE_CXX_COMPILER}" -dumpspecs
            RESULT_VARIABLE _gpolice_dumpspecs_result
            OUTPUT_VARIABLE _gpolice_dumpspecs
            ERROR_VARIABLE _gpolice_dumpspecs_error)
        if(NOT _gpolice_dumpspecs_result EQUAL 0)
            message(FATAL_ERROR
                "Unable to inspect GNU linker specs: "
                "${_gpolice_dumpspecs_error}")
        endif()

        string(REPLACE "\r\n" "\n"
            _gpolice_dumpspecs "${_gpolice_dumpspecs}")
        string(REGEX MATCH "\\*endfile:\n([^\n]*)"
            _gpolice_endfile_match "${_gpolice_dumpspecs}")
        set(_gpolice_endfile_spec "${CMAKE_MATCH_1}")
        set(_gpolice_default_manifest_spec
            "%{!shared:%:if-exists(default-manifest.o%s)}")
        if(NOT _gpolice_endfile_match
           OR NOT _gpolice_endfile_spec MATCHES "default-manifest\\.o")
            message(FATAL_ERROR
                "GNU supplies default-manifest.o through an unrecognized "
                "endfile spec")
        endif()

        string(REPLACE "${_gpolice_default_manifest_spec}" ""
            _gpolice_endfile_spec "${_gpolice_endfile_spec}")
        set(_gpolice_specs
            "${CMAKE_CURRENT_BINARY_DIR}/gpolice-no-default-manifest.specs")
        set(_gpolice_specs_content
            "%rename endfile gpolice_original_endfile\n\n"
            "*endfile:\n${_gpolice_endfile_spec}\n")
        string(CONCAT _gpolice_specs_content ${_gpolice_specs_content})
        if(EXISTS "${_gpolice_specs}")
            file(READ "${_gpolice_specs}" _gpolice_old_specs_content)
        else()
            set(_gpolice_old_specs_content "")
        endif()
        if(NOT _gpolice_old_specs_content STREQUAL _gpolice_specs_content)
            file(WRITE "${_gpolice_specs}" "${_gpolice_specs_content}")
        endif()
        target_link_options(psx-runtime PRIVATE "-specs=${_gpolice_specs}")
        set_property(TARGET psx-runtime APPEND PROPERTY
            LINK_DEPENDS "${_gpolice_specs}")
        message(STATUS
            "G-Police: GNU default-manifest.o suppressed for psx-runtime")
    endif()
endif()

# Stage runtime configs next to the exe for direct build/ launches. Only copy
# files that exist — never fail POST_BUILD when game_options.toml is absent.
foreach(_PSX_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-runtime POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${_PSX_RUNTIME_CONFIG}"
            COMMENT "Staging ${_PSX_RUNTIME_CONFIG}"
            VERBATIM)
    endif()
endforeach()
