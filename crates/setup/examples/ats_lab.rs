//! Builds screen resources from the real local ATS installation, without changing the game or saves.
use std::path::PathBuf;
use westplay_mapdata::files::GameFiles;
use westplay_setup::{
    cab_mark,
    game::{FoundBy, Game},
    game_mod,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args_os().skip(1);
    let install = PathBuf::from(args.next().ok_or("usage: ats_lab <ATS install> <output directory>")?);
    let output = PathBuf::from(args.next().ok_or("missing output directory")?);
    let game = Game::at(&install, FoundBy::Chosen).ok_or("Not an ATS installation")?;
    let files = game.files()?;
    let empty = GameFiles::new(vec![]);
    let (bytes, built) = game_mod::build(&files, &[], &empty, &cab_mark::Marks::default())?;
    if !built.patched.contains(&"ford-f150-2023") {
        return Err("The local Ford GPS could not be patched; no compatible Ford screen was generated".into());
    }
    std::fs::create_dir_all(&output)?;
    let archive = game_mod::install(&bytes, &output)?;
    let report = serde_json::json!({
        "game": game.dir, "version": game.version.map(|v| v.to_string()),
        "screenLayoutsPatched": built.patched, "archive": archive,
        "archiveBytes": bytes.len(), "baseMap": files.base_map(),
        "inGameVerified": false,
        "note": "Built from real installed files. Rendering, input, navigation and DLC authorization require a real game session."
    });
    std::fs::write(output.join("screen-resource-report.json"), serde_json::to_vec_pretty(&report)?)?;
    println!("{report}");
    Ok(())
}
