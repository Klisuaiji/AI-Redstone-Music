================ Redstone Music Box (generic framework · MC 26.2) ================
This pack contains no songs: it is a box offering "player + song menu + lyrics + per-dimension ban",
Songs are registered by scripts/add_to_musicbox.py (each song lives in data/rmb/function/song/<number>/).

[Install] Drop the zip into the world's datapacks/ → /reload

[Player commands]
  /trigger menu             get / take back the music box (enchanted, cannot be placed or dropped; if lost it is automatically re-issued)
  /trigger lrc              toggle lyrics (shown in the action bar = the small text near the bottom of the screen, switches with the music)
  /trigger play set <number>   request a song; you can also use /function rmb:play {song:song_name}

[Music box controls]
  Left click        = previous song
  Double click / hold left = pause · play
  Right click        = next song
  Double right click        = open / close the song menu (click a song name in chat to play it)

[Admin commands (/function)]
  rmb:dim/ban       ban playback in the executor's dimension
  rmb:dim/unban     lift the ban for the executor's dimension
  rmb:dim/status    show ban status
  rmb:dim/clear     lift all dimension bans
  rmb:dim/on|off    master switch for the per-dimension ban
  rmb:uninstall     uninstall (clear items / clear interaction entities / remove scoreboards)

[Adding songs]
  python3 scripts/add_to_musicbox.py --box <this datapack directory> --song song.json [--lrc lyrics.lrc]
  (you can also pass a .mid directly; the script arranges it automatically first)
  /reload is required before the change takes effect.

[Scoreboards (all abbreviated)]
  menu / lrc / play                                      player trigger
  mb_song mb_lyc mb_pls mb_rct mb_hol mb_hct mb_don
  mb_uct mb_udo mb_msg mb_cfg                            internal state
  music_type / nbs_s / nbs_t                             song playback contract (do not rename)

[Version] Requires MC 1.21.5+ (uses the items entity item predicate and component syntax); this pack's pack.mcmeta targets 26.2.
        To switch versions, change the pack.mcmeta format numbers and directory names as described in references/datapack.md.
