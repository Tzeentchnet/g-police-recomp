#include <stdio.h>

#include "cpu_state.h"
#include "mod_plugins.h"

#define GPOLICE_DRAW_DISTANCE_PLUGIN "gpolice.extended-draw-distance"
#define GPOLICE_DRAW_DISTANCE 145000u
#define GPOLICE_DRAW_DISTANCE_STORE 0xAC22453Cu
#define GPOLICE_DRAW_DISTANCE_NORMAL_PC 0x80020FB8u
#define GPOLICE_DRAW_DISTANCE_SPECIAL_PC 0x80020FCCu

static int registration_complete;

static void apply_extended_draw_distance(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!registration_complete) {
        return;
    }

    cpu->gpr[2] = GPOLICE_DRAW_DISTANCE;
    psx_mod_counter_add(
        GPOLICE_DRAW_DISTANCE_PLUGIN ".stores-overridden", 1u);
}

PSX_MOD_CONSTRUCTOR(gpolice_register_extended_draw_distance) {
    const int normal_registered = psx_mod_register_instruction_plugin(
        GPOLICE_DRAW_DISTANCE_PLUGIN,
        GPOLICE_DRAW_DISTANCE_NORMAL_PC,
        GPOLICE_DRAW_DISTANCE_STORE,
        apply_extended_draw_distance);
    const int special_registered = psx_mod_register_instruction_plugin(
        GPOLICE_DRAW_DISTANCE_PLUGIN,
        GPOLICE_DRAW_DISTANCE_SPECIAL_PC,
        GPOLICE_DRAW_DISTANCE_STORE,
        apply_extended_draw_distance);

    registration_complete = normal_registered && special_registered;
    if (!registration_complete) {
        fprintf(
            stderr,
            "psxrecomp: G-Police extended draw-distance plugin registration "
            "failed\n");
        fflush(stderr);
    }
}
