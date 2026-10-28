//! Independent compiler-generated ABI description for tools/ats_probe.py.
//! Does not open a mapping or interact with a game.

use std::mem::{align_of, offset_of, size_of};
use std::sync::atomic::AtomicU32;

use westplay_shared::*;

fn show<T>(name: &str, fields: &[(&str, usize)], comma: bool) {
    if comma {
        print!(",");
    }
    print!("\"{name}\":{{\"size\":{},\"align\":{},\"fields\":{{", size_of::<T>(), align_of::<T>());
    for (index, (field, offset)) in fields.iter().enumerate() {
        if index > 0 {
            print!(",");
        }
        print!("\"{field}\":{offset}");
    }
    print!("}}}}");
}

macro_rules! fields {
    ($kind:ty, $($field:ident),+ $(,)?) => {
        &[$((stringify!($field), offset_of!($kind, $field))),+]
    };
}

fn seq<T: Plain>(name: &str) {
    // SeqLock is repr(C): AtomicU32 then UnsafeCell<T>, whose alignment is T's.
    // Private fields are not exposed by the public crate; check its compiler-derived
    // size/alignment as well as the repr(C) value offset.
    show::<SeqLock<T>>(
        name,
        &[("sequence", 0), ("value", size_of::<AtomicU32>().next_multiple_of(align_of::<T>()))],
        true,
    );
}

fn main() {
    // The sole string has backslashes: escape them for JSON without extra dependencies.
    let name = bridge_name().replace('\\', "\\\\");
    print!("{{\"bridge_name\":\"{name}\",\"magic\":{BRIDGE_MAGIC},\"version\":{BRIDGE_VERSION},\"types\":{{");
    show::<Bridge>("Bridge", fields!(Bridge, magic, version, plugin, host, route, typing), false);
    show::<PluginBlock>(
        "PluginBlock",
        fields!(
            PluginBlock,
            pid,
            heartbeat,
            adapter_luid_low,
            adapter_luid_high,
            screen_layout,
            screen_frame,
            cab_frame,
            truck_supported,
            telemetry,
            truck,
            job,
            pointer,
            nearby,
            keybind_presses
        ),
        true,
    );
    show::<HostBlock>(
        "HostBlock",
        fields!(
            HostBlock,
            pid,
            heartbeat,
            frame_generation,
            frame_width,
            frame_height,
            frame_seq,
            screen_enabled,
            interaction_key,
            interaction_toggle,
            keybinds
        ),
        true,
    );
    show::<RouteBlock>(
        "RouteBlock",
        fields!(RouteBlock, action, node, request, answered, answer, vias, via_count),
        true,
    );
    show::<TypingBlock>("TypingBlock", fields!(TypingBlock, selection, state, keys), true);
    show::<PointerBlock>("PointerBlock", fields!(PointerBlock, active, dx, dy, wheel, buttons), true);
    show::<Telemetry>(
        "Telemetry",
        fields!(
            Telemetry,
            x,
            y,
            z,
            heading,
            pitch,
            roll,
            speed,
            engine_rpm,
            gear,
            displayed_gear,
            cruise_control_speed,
            fuel,
            fuel_range,
            navigation_distance,
            navigation_time,
            navigation_speed_limit,
            game_time,
            local_scale,
            dashboard_backlight,
            electric_enabled,
            engine_enabled,
            parking_brake,
            low_beam,
            high_beam,
            left_blinker,
            right_blinker,
            paused,
            head_x,
            head_y,
            head_z,
            head_heading,
            head_pitch,
            camera_known,
            camera_x,
            camera_y,
            camera_z,
            cabin_x,
            cabin_y,
            cabin_z,
            steering,
            multiplayer_time_offset
        ),
        true,
    );
    show::<TruckInfo>("TruckInfo", fields!(TruckInfo, brand_id, brand, id, name, head, plate, plate_country), true);
    show::<JobInfo>(
        "JobInfo",
        fields!(
            JobInfo,
            active,
            cargo_loaded,
            special,
            cargo,
            cargo_mass,
            source_city,
            source_company,
            destination_city,
            destination_company,
            delivery_time,
            planned_distance_km,
            income
        ),
        true,
    );
    show::<Nearby>("Nearby", fields!(Nearby, frame, server, local, count, players), true);
    show::<NearbyPlayer>("NearbyPlayer", fields!(NearbyPlayer, id, heading, x, z), true);
    seq::<Telemetry>("SeqTelemetry");
    seq::<TruckInfo>("SeqTruck");
    seq::<JobInfo>("SeqJob");
    seq::<Nearby>("SeqNearby");
    show::<KeyQueue<64>>("KeyQueue64", &[], true);
    println!("}}}}");
}
