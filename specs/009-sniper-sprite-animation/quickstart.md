# 快速開始與驗證：狙擊者 Q 版像素角色與八方向動畫

## 前置條件

- Windows 桌面環境。
- Python 3.11 或更新版本。
- 專案虛擬環境已安裝 `pvpve_escape/requirements.txt` 中的依賴。
- 狙擊者資產已放入 `pvpve_escape/assets/characters/sniper/`，包含 8 張待機、32 張移動與 32 張攻擊圖片，共 72 張。
- 正式素材依 `pixel-character-animation` 技能先完成逐張創意 QA，再完成透明與尺寸 QA。

## 資產快速檢查

在專案根目錄執行 PowerShell：

```powershell
$assetRoot = 'pvpve_escape/assets/characters/sniper'
(Get-ChildItem -LiteralPath $assetRoot -Recurse -File -Filter '*.png').Count
```

預期結果為 `72`。每張圖片必須是 1024×1024 RGBA、四個角落為透明像素、`alpha > 0` 的角色像素未貼住或超出邊界，同方向動畫幀中心偏移不超過 16 個來源像素，並通過逐張人工檢查。資產 QA 與品質閘門以 `alpha >= 64` 判定角色外框；破陣者仍依可見外框顯示，狙擊者則先以各方向完整動畫的身體核心聯合外框統一縮放，武器外伸不參與角色本體比例，再保留固定來源畫布顯示，兩個門檻的用途不同，必須在測試與資產 QA 中保持一致。

人工檢查必須確認：

1. 偵察狙擊兵的深藍／藍灰身份、長槍、瞄具與青藍識別色在小尺寸仍可辨識。
2. 右、右下、下、左下、左、左上、上、右上八個方向語意正確；上方三個方向顯示背面。
3. 移動四格有交替步伐，攻擊四格有持槍瞄準／後座變化；整張角色的頭盔／面罩大小一致，角色比例、槍械連接與錨點一致。
4. 沒有文字、UI、背景、棋盤格、陰影、光環、煙霧、漂浮粒子、空白幀、裁切或孤立像素。

若問題是角色創意、方向、比例、持槍關係或像素內容錯誤，使用角色製作技能重新生成該張；若只是可明確判定的 alpha、畫布或置中格式問題，才可使用不改角色內容的確定性整理。

## 自動測試

在專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q
.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_performance -q
.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q
.\.venv\Scripts\python.exe -m compileall -q pvpve_escape
git diff --check
```

在新增測試前，先將當時既有的 245 個測試案例名稱與通過結果記錄在本文件的「驗證紀錄」；新增測試後，全套測試的總數會增加，不再把 `245/245` 當作最終總數門檻。預期結果是已記錄的基線案例與新增的狙擊者案例全部通過；`test_sprite_performance` 另須記錄平均 FPS、最大單幀間隔與量測期間的 `pygame.image.load` 呼叫次數。

### 基線案例快照（2026-08-29）

新增狙擊者測試前，以下 245 個既有案例均為 `OK`：

- [X] `test_aiming.AimGuideGeometryTests.test_breacher_preview_uses_the_authoritative_cone_constants` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_dash_preview_simulates_first_thin_wall_break_then_stops_at_next_wall` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_endpoint_is_limited_to_the_world_boundary` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_guides_are_read_only_and_invalid_resources_only_change_color_state` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_line_and_path_guides_stop_at_the_same_confirmed_wall_as_gameplay` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_omitting_obstacles_keeps_the_legacy_preview_result` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_primary_guides_use_the_character_specific_geometry` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_tactical_guides_expose_dash_shield_and_bounded_control` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_ultimate_and_tactical_guides_share_the_same_boundary_rule` — 通過
- [X] `test_aiming.AimGuideGeometryTests.test_ultimate_guides_describe_each_role_specific_shape` — 通過
- [X] `test_ammo_lifecycle.AmmoLifecycleTests.test_same_frame_primary_cast_cannot_recover_before_consuming_ammo` — 通過
- [X] `test_ammo_lifecycle.AmmoLifecycleTests.test_ultimate_and_tactical_alone_do_not_block_ammo_recovery` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_center_edges_and_partially_intersecting_pellet_paths_are_hit` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_completely_outside_pellet_paths_and_range_are_not_hit` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_cone_origin_is_fixed_even_when_owner_moves_after_cast` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_damage_equals_the_number_of_hit_pellets` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_dash_integration_breaks_one_adjacent_wall_cell_and_keeps_the_next` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_dead_target_stops_remaining_pellet_events` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_each_target_gets_at_most_five_pellet_hits_across_frames` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_front_sweep_hits_when_target_is_crossed_between_updates` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_pellet_boundaries_are_stable_across_repeated_runs` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_targets_near_origin_and_multiple_targets_are_resolved` — 通過
- [X] `test_breach_cone.BreachPelletRuleTests.test_widened_pellets_cover_every_gap_at_max_range` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_all_abilities_survive_twenty_repeated_cast_smoke_runs` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_breach_cone_marker_never_changes_target_state_without_pellets` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_breach_pellets_apply_damage_independently_of_cone_marker` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_every_ultimate_and_tactical_action_has_a_rule_effect` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_hit_blocked_invulnerable_and_control_feedback_repeat_twenty_times` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_primary_effects_are_removed_after_their_lifecycle_ends` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_primary_effects_snapshot_origin_direction_range_and_metadata` — 通過
- [X] `test_combat_effects.CombatEffectDataTests.test_primary_ultimate_and_tactical_effect_kinds_are_distinct` — 通過
- [X] `test_config.ConfigValueTests.test_confirmed_map_layout_matches_editor_submission` — 通過
- [X] `test_config.ConfigValueTests.test_confirmed_map_layout_stays_inside_world_bounds` — 通過
- [X] `test_config.ConfigValueTests.test_confirmed_red_overlaps_are_explicitly_retained` — 通過
- [X] `test_config.ConfigValueTests.test_game_frame_rate_cap_is_120_fps` — 通過
- [X] `test_config.ConfigValueTests.test_gui_opacity_accepts_inclusive_endpoints` — 通過
- [X] `test_config.ConfigValueTests.test_gui_opacity_clamps_out_of_range_and_invalid_values` — 通過
- [X] `test_config.ConfigValueTests.test_gui_opacity_defaults_and_alpha_are_stable` — 通過
- [X] `test_config.ConfigValueTests.test_saved_editor_snapshot_matches_formal_layout_constants` — 通過
- [X] `test_config.ConfigValueTests.test_terrain_visual_and_regeneration_constants_are_stable` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_auto_aim_does_not_choose_a_target_behind_a_wall` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_auto_aim_uses_the_configured_past_position` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_fired_projectile_keeps_the_historical_direction_and_does_not_hit_immediately` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_lookback_number_can_be_changed_without_changing_aim_code` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_tab_toggles_auto_aim_during_play` — 通過
- [X] `test_game_features.AutoAimHistoryTests.test_zero_lookback_uses_the_current_target_position` — 通過
- [X] `test_game_features.IntroScreenTests.test_intro_can_render_and_enter_moves_to_selection` — 通過
- [X] `test_game_features.MonsterCombatRegressionTests.test_chaser_and_brute_keep_contact_attack_only` — 通過
- [X] `test_game_features.MonsterCombatRegressionTests.test_shooter_keeps_attack_range_preferred_range_and_slow_projectile` — 通過
- [X] `test_game_features.MonsterCombatRegressionTests.test_wander_and_return_never_attack` — 通過
- [X] `test_game_features.MonsterNavigationIntegrationTests.test_each_monster_type_reaches_a_wall_blocked_target_without_jumping` — 通過
- [X] `test_game_features.MonsterNavigationIntegrationTests.test_shooter_can_leave_the_navigation_clearance_at_a_long_wall_corner` — 通過
- [X] `test_game_features.MonsterNavigationIntegrationTests.test_shooter_does_not_stall_when_preferred_position_is_inside_a_wall_corner` — 通過
- [X] `test_game_features.MonsterNavigationIntegrationTests.test_shooter_falls_back_to_reachable_target_when_preferred_area_is_sealed` — 通過
- [X] `test_game_features.MonsterRosterTests.test_each_camp_has_one_of_each_monster_type` — 通過
- [X] `test_game_features.MonsterRosterTests.test_monsters_start_in_wander_without_shared_navigation_state` — 通過
- [X] `test_game_features.MonsterRosterTests.test_shooter_projectile_can_be_dodged_before_it_reaches_the_player` — 通過
- [X] `test_game_features.MonsterRosterTests.test_shooter_spawns_a_slow_projectile_instead_of_contact_damage` — 通過
- [X] `test_game_features.MonsterWanderIntegrationTests.test_each_monster_type_reaches_two_safe_distinct_wander_points_at_half_speed` — 通過
- [X] `test_game_features.MonsterWanderIntegrationTests.test_monster_returns_to_camp_before_wandering_and_does_not_attack` — 通過
- [X] `test_game_features.MonsterWanderIntegrationTests.test_respawn_clears_chase_wander_and_navigation_state` — 通過
- [X] `test_game_features.MonsterWanderIntegrationTests.test_wander_candidates_use_the_expanded_700px_radius` — 通過
- [X] `test_game_features.TerrainSkillIntegrationTests.test_breacher_ultimate_breaks_only_intersecting_formal_cells` — 通過
- [X] `test_main.GameApplicationFlowTests.test_focus_death_respawn_and_restart_state_reset_repeat_twenty_times` — 通過
- [X] `test_main.GameApplicationFlowTests.test_focus_loss_and_death_clear_channel_before_respawn` — 通過
- [X] `test_main.GameApplicationFlowTests.test_new_match_rebuilds_all_terrain_cell_states` — 通過
- [X] `test_main.GameApplicationFlowTests.test_restart_key_during_playing_returns_to_character_selection` — 通過
- [X] `test_main.GameApplicationFlowTests.test_restart_resets_controller_state_and_new_match_attack_state` — 通過
- [X] `test_map_assets.MapAssetTests.test_all_runtime_tiles_exist_are_100px_and_fully_opaque` — 通過
- [X] `test_map_assets.MapAssetTests.test_each_tile_loads_once_and_reuses_the_cached_surface` — 通過
- [X] `test_map_assets.MapAssetTests.test_missing_wall_tile_uses_the_existing_procedural_fallback` — 通過
- [X] `test_map_editor.MapEditorTerrainTests.test_loading_old_rectangles_normalizes_to_single_priority_cells` — 通過
- [X] `test_map_editor.MapEditorTerrainTests.test_save_writes_only_aligned_100px_items_after_normalization` — 通過
- [X] `test_map_performance.MapPerformanceTests.test_cached_map_rendering_maintains_55_fps_after_warmup` — 通過
- [X] `test_navigation.NavigationTestCase.test_diagonal_route_does_not_cut_through_a_wall_corner` — 通過
- [X] `test_navigation.NavigationTestCase.test_full_wall_returns_no_path` — 通過
- [X] `test_navigation.NavigationTestCase.test_goal_inside_wall_returns_no_path` — 通過
- [X] `test_navigation.NavigationTestCase.test_goal_touching_a_wall_can_use_the_nearest_safe_approach_cell` — 通過
- [X] `test_navigation.NavigationTestCase.test_grid_to_world_returns_cell_centers` — 通過
- [X] `test_navigation.NavigationTestCase.test_larger_monster_radius_cannot_use_a_narrow_corridor` — 通過
- [X] `test_navigation.NavigationTestCase.test_monster_keeps_approaching_when_player_is_touching_a_thick_wall` — 通過
- [X] `test_navigation.NavigationTestCase.test_navigation_module_has_a_pure_path_entry_point` — 通過
- [X] `test_navigation.NavigationTestCase.test_new_target_chooses_nearest_alive_player_then_player_id` — 通過
- [X] `test_navigation.NavigationTestCase.test_new_target_requires_alive_player_visible_within_aggro_radius` — 通過
- [X] `test_navigation.NavigationTestCase.test_no_route_keeps_monster_safe_and_retries_after_terrain_changes` — 通過
- [X] `test_navigation.NavigationTestCase.test_path_goes_around_a_rectangular_wall_with_clearance` — 通過
- [X] `test_navigation.NavigationTestCase.test_path_segments_match_the_existing_swept_wall_collision` — 通過
- [X] `test_navigation.NavigationTestCase.test_path_stays_inside_world_safe_boundary` — 通過
- [X] `test_navigation.NavigationTestCase.test_wall_snapshot_invalidates_paths_for_three_behaviors_in_one_camp` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_attack_action_restarts_attack_timer_but_dash_and_shield_do_not` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_control_hit_restarts_damage_wait_even_without_direct_damage` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_dead_player_never_regenerates_and_new_life_resets_timers` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_dead_player_timers_do_not_accumulate_during_respawn_wait` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_exact_five_second_boundary_starts_regeneration` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_hit_and_attack_markers_reset_independent_timers` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_non_attack_dash_can_regenerate_on_the_next_update` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_regeneration_does_not_start_before_five_seconds` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_regeneration_scales_with_delta_time_and_clamps_to_maximum` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_shield_or_invulnerability_hit_still_restarts_damage_wait` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_world_control_effect_counts_as_a_hit_for_a_player_target` — 通過
- [X] `test_regeneration.PlayerRegenerationRuleTests.test_world_updates_regeneration_after_same_frame_hit_and_attack_resolution` — 通過
- [X] `test_rendering.BreacherVisualRenderingTests.test_common_player_visual_selects_attack_over_move` — 通過
- [X] `test_rendering.BreacherVisualRenderingTests.test_qwe_update_selected_tactical_index` — 通過
- [X] `test_rendering.BreacherVisualRenderingTests.test_selection_and_roster_use_idle_sprite_but_other_roles_keep_geometry` — 通過
- [X] `test_rendering.BreacherVisualRenderingTests.test_unavailable_breacher_sprite_falls_back_to_existing_geometry` — 通過
- [X] `test_rendering.BreacherVisualRenderingTests.test_world_uses_common_visual_entry_for_live_players` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_battle_hud_no_longer_contains_fixed_attack_prompts` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_death_countdown_is_private_to_the_current_viewer` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_draw_world_centralizes_private_visibility_for_all_six_players` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_local_death_countdown_uses_large_centered_pygame_font_text` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_local_overhead_clamps_resources_and_health_boundaries_repeatedly` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_local_overhead_follows_player_screen_coordinates_twenty_times` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_local_overhead_gadget_color_updates_for_ready_cooldown_and_death` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_local_overhead_shows_public_and_private_state` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_other_player_overhead_only_contains_public_information` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_other_player_overlay_is_culled_outside_viewport_and_returns_when_visible` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_overhead_edge_clamp_and_long_identity_use_shared_layout_rules` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_overhead_vertical_clamp_keeps_the_information_block_on_screen` — 通過
- [X] `test_rendering.OverheadRenderingTests.test_selection_page_contains_role_attack_and_operation_hints` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_active_control_and_defense_states_are_visible_on_their_targets` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_all_combat_effect_states_render_without_external_assets` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_all_confirmed_walls_and_bushes_are_rendered_on_the_map_layer` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_camera_positions_keep_tile_pixels_aligned_and_clip_partial_tiles_naturally` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_confirmed_terrain_is_visible_in_the_actual_game_viewport_after_camera_moves` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_control_preview_endpoint_matches_released_control_zone` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_controller_exposes_press_hold_release_and_focus_loss_edges` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_destroyed_terrain_is_removed_from_the_next_map_draw` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_destroying_one_cell_leaves_neighbor_and_thick_wall_tiles_visible` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_every_role_primary_and_ultimate_creates_a_visual_effect` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_every_tactical_action_creates_a_visual_effect` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_flying_effect_render_data_uses_previous_position_and_mine_arming` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_formal_terrain_and_ground_use_100px_tile_pixels` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_gui_panels_use_local_alpha_without_fading_world_or_text` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_hold_preview_is_visible_for_each_role_without_mutating_match` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_human_player_is_rendered_without_a_base_circle_when_match_starts` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_live_skill_input_changes_ultimate_and_control_state` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_live_sniper_mouse_input_reaches_the_same_collision_path_as_direct_input` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_mouse_and_space_events_trigger_skill_input_flags` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_non_playing_phase_blocks_held_skill_until_a_new_press` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_preview_priority_and_invalid_state_are_observable` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_repeated_ability_rendering_smoke_runs_twenty_times_per_slot` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_selection_and_result_panels_render_at_all_supported_opacities` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_sniper_ultimate_line_stays_at_its_cast_position` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_traditional_chinese_text_is_drawn` — 通過
- [X] `test_rendering.TraditionalChineseFontTests.test_traditional_chinese_uses_a_system_cjk_font` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_boomerang_can_damage_the_same_target_once_on_each_direction` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_character_and_monster_balance_table_is_centralized` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_damage_order_applies_shield_then_reduction_and_final_clamp` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_fixed_ttk_ranges_use_the_new_role_values` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_four_flying_roles_hold_speed_within_five_percent_for_twenty_runs` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_hold_release_resource_checks_and_siphoner_channel` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_insufficient_resources_never_cast_on_release` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_non_channel_primary_only_casts_on_release` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_non_channel_slots_and_quick_taps_are_single_casts` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_player_zero_spawn_is_at_least_200px_from_every_monster_camp` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_projectile_speed_snapshots_and_non_flying_effects` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_projectile_sweeps_and_controller_mine_only_arms_at_landing` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_projectiles_move_at_configured_speed_for_ten_frames` — 通過
- [X] `test_rules.AimAndProjectileRuleTests.test_siphoner_full_channel_has_eight_ticks_in_1_2_seconds` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_conditional_passives_change_damage_or_control_duration` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_control_tactical_slows_and_releases_monsters` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_each_role_can_create_primary_and_ultimate_actions` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_each_role_can_fire_primary_through_gameplay_input` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_each_ultimate_applies_a_gameplay_effect_to_a_world_target` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_six_roles_have_distinct_primary_passive_and_ultimate_data` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_sniper_impact_marker_stays_at_the_position_where_damage_was_applied` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_sniper_projectile_does_not_damage_a_target_off_its_visible_path` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_sniper_projectile_hits_the_first_target_on_its_visible_path` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_sniper_projectile_records_a_blocked_hit_when_shield_absorbs_damage` — 通過
- [X] `test_rules.CharacterDefinitionTests.test_sniper_quick_click_fires_but_siphoner_quick_click_does_not_channel` — 通過
- [X] `test_rules.CombatRuleTests.test_ammo_capacity_and_continuous_recovery` — 通過
- [X] `test_rules.CombatRuleTests.test_blocked_ammo_recovery_resets_timer_and_waits_after_release` — 通過
- [X] `test_rules.CombatRuleTests.test_damage_adds_energy_and_final_monster_hit_gives_only_one_upgrade` — 通過
- [X] `test_rules.CombatRuleTests.test_death_clears_state_and_respawn_restores_basic_state` — 通過
- [X] `test_rules.CombatRuleTests.test_energy_is_capped_and_upgrade_is_capped` — 通過
- [X] `test_rules.CombatRuleTests.test_full_ammo_and_dead_player_keep_recovery_timer_zero` — 通過
- [X] `test_rules.CombatRuleTests.test_monster_kill_removes_owned_effects_in_the_same_update` — 通過
- [X] `test_rules.CombatRuleTests.test_monster_respawns_after_fixed_delay` — 通過
- [X] `test_rules.CombatRuleTests.test_primary_attack_active_covers_hold_charge_and_cooldown` — 通過
- [X] `test_rules.CombatRuleTests.test_tactical_cooldown_is_fixed_and_resets_after_time` — 通過
- [X] `test_rules.CombatRuleTests.test_tactical_cooldown_is_preserved_and_frozen_while_dead` — 通過
- [X] `test_rules.ExtractionRuleTests.test_extraction_requires_activation_and_accumulates_per_player` — 通過
- [X] `test_rules.ExtractionRuleTests.test_extraction_uses_only_time_after_activation_and_before_timeout` — 通過
- [X] `test_rules.ExtractionRuleTests.test_extraction_wins_before_timeout_and_timeout_has_no_winner` — 通過
- [X] `test_rules.ExtractionRuleTests.test_first_completion_and_same_tick_use_lowest_player_id` — 通過
- [X] `test_rules.ExtractionRuleTests.test_leaving_resets_only_that_players_progress` — 通過
- [X] `test_rules.PlayerSetupTests.test_match_has_six_unique_players_and_all_tactics` — 通過
- [X] `test_rules.RestartTests.test_new_match_does_not_keep_previous_player_state` — 通過
- [X] `test_rules.WorldBoundaryTests.test_camera_is_clamped_after_following_target` — 通過
- [X] `test_rules.WorldBoundaryTests.test_dash_preview_uses_move_direction_when_it_is_available` — 通過
- [X] `test_rules.WorldBoundaryTests.test_diagonal_boomerang_uses_the_same_bounded_ray_as_its_aim_guide` — 通過
- [X] `test_rules.WorldBoundaryTests.test_diagonal_dash_and_control_land_on_the_preview_endpoint` — 通過
- [X] `test_rules.WorldBoundaryTests.test_instant_attack_visuals_stay_at_their_cast_position` — 通過
- [X] `test_rules.WorldBoundaryTests.test_player_position_is_clamped_inside_world` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_all_72_assets_have_the_required_shape_and_transparency` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_animation_frame_request_uses_attack_priority_and_four_frame_ranges` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_breacher_actions_start_attack_visual_state` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_clearing_sprite_cache_forces_each_image_to_be_read_again` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_death_and_respawn_clear_animation_progress_without_changing_facing` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_direction_quantization_uses_eight_stable_sectors` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_displayed_assets_normalize_visible_extent_to_requested_canvas` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_failed_asset_is_cached_and_not_reloaded_every_frame` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_invalid_dimensions_and_opaque_backgrounds_return_unavailable_result` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_invalid_queries_return_unavailable_result_and_record_error` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_preload_reads_and_extracts_all_72_images_once` — 通過
- [X] `test_sprite_animation.BreacherSpriteAssetTests.test_valid_asset_is_scaled_with_cache_identity` — 通過
- [X] `test_terrain.NormalizedTerrainTests.test_compatibility_builders_share_cross_type_deduplication` — 通過
- [X] `test_terrain.NormalizedTerrainTests.test_confirmed_terrain_is_expanded_to_independent_aligned_cells` — 通過
- [X] `test_terrain.NormalizedTerrainTests.test_normalization_removes_overlap_with_thick_thin_bush_priority` — 通過
- [X] `test_terrain.TerrainCellDestructionTests.test_boundary_contact_keeps_existing_epsilon_policy` — 通過
- [X] `test_terrain.TerrainCellDestructionTests.test_dash_path_reports_only_the_first_thin_wall_before_the_next_blocker` — 通過
- [X] `test_terrain.TerrainCellDestructionTests.test_path_destruction_updates_only_the_first_adjacent_thin_wall` — 通過
- [X] `test_terrain.TerrainCellDestructionTests.test_radius_destruction_updates_only_intersecting_cells_and_never_thick_wall` — 通過
- [X] `test_terrain.TerrainCellDestructionTests.test_segment_destruction_updates_only_crossed_bush_cells` — 通過
- [X] `test_terrain.TerrainDestructionAndVisibilityTests.test_area_and_segment_policies_remove_thin_walls_and_bushes` — 通過
- [X] `test_terrain.TerrainDestructionAndVisibilityTests.test_only_first_thin_wall_on_a_path_can_be_destroyed` — 通過
- [X] `test_terrain.TerrainDestructionAndVisibilityTests.test_player_visibility_is_self_visible_and_otherwise_bush_dependent` — 通過
- [X] `test_terrain.TerrainDestructionAndVisibilityTests.test_segment_destruction_does_not_remove_bushes_that_are_not_crossed` — 通過
- [X] `test_terrain.TerrainDestructionAndVisibilityTests.test_terrain_interaction_enum_has_explicit_breaking_policies` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_axis_separated_movement_stops_and_diagonal_movement_slides` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_boomerang_return_does_not_cross_a_wall_if_owner_is_on_the_other_side` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_breacher_primary_blocks_thin_wall_without_breaking_it` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_breacher_ultimate_area_breaks_thin_wall_and_bush_but_not_thick_wall` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_circle_rectangle_boundary_and_corner_contact_are_consistent` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_create_match_rebuilds_the_confirmed_terrain_for_every_new_round` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_dash_breaks_only_the_first_thin_wall_then_stops_at_the_next_wall` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_diagonal_movement_cannot_cut_through_a_wall_corner` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_diagonal_movement_keeps_sliding_after_contact_with_a_thick_wall` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_each_built_terrain_collection_is_independent` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_first_wall_path_returns_the_nearest_wall_and_radius_adjusted_point` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_knockback_stops_at_a_wall_instead_of_pushing_a_target_through_it` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_monster_movement_also_stops_at_the_same_wall_geometry` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_non_qualified_primary_and_non_dash_tactical_do_not_destroy_walls_or_bushes` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_path_can_leave_a_wall_boundary_without_a_false_block` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_path_endpoint_keeps_requested_end_when_no_wall_exists` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_player_diagonal_input_continues_along_a_thick_wall` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_player_movement_stays_in_front_of_a_confirmed_wall_for_repeated_steps` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_projectile_stops_at_the_first_wall_and_cannot_hit_a_wall_behind_target` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_snapshot_keeps_obstacle_identity_kind_and_bounds` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_update_world_uses_the_same_wall_collision_for_human_input` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_world_rect_exposes_edges_center_and_contains` — 通過
- [X] `test_terrain.TerrainGeometryTests.test_world_updates_monsters_after_player_breaks_thin_wall` — 通過
- [X] `test_visibility.BushViewerRenderingTests.test_inactive_bush_restores_other_view_and_roster_without_revealing_beforehand` — 通過
- [X] `test_visibility.BushViewerRenderingTests.test_self_view_keeps_role_and_overlay_while_other_view_hides_them` — 通過
- [X] `test_visibility.BushViewerRenderingTests.test_visibility_does_not_change_known_target_or_damage_state` — 通過

## 驗證紀錄

每次執行 T006、T008、T027～T030 後，依序追加日期、命令或手動情境、實際結果、測量值與通過判定；資產 QA、基線測試快照、效能量測與手動驗收都集中記錄於此，避免只保留口頭確認。

- 2026-08-29｜T006 資產 QA：逐張檢查 idle 8、move 32、attack 32，共 72 張；結果 `checked=72 expected=72`、`failures=0`、`ASSET_QA=PASS`。所有圖片均為 1024×1024、32-bit RGBA，四角與外框透明，alpha≥64 可見外框未貼邊；同方向動畫幀中心偏移檢查通過。生成器初始輸出的棋盤格／尺寸問題僅以邊界連通背景移除、固定畫布與最近鄰縮放整理，未重畫角色內容。
- 2026-08-29｜T008 基線測試：`.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -v`，新增狙擊者測試前共 245/245 通過；完整案例名稱已記錄於上方「基線案例快照」。
- 2026-08-29｜T008 測試先行：執行 `.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation.SniperSpriteAssetTests -v`，在尚未實作角色中立載入器時三個狙擊者案例均以 `AttributeError: clear_character_sprite_cache` 失敗，確認測試能辨識缺少功能。
- 2026-08-29｜T011～T017 Foundational／US1 檢查點：`.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -v`，共 72 項通過；包含狙擊者 72 張索引、共用快取三種尺寸、八方向分界、移動／攻擊優先、三類成功動作觸發、對局像素繪製與幾何 fallback。
- 2026-08-29｜T018～T024 US2／US3 檢查點：同一組 headless rendering／sprite 測試共 72 項通過；狙擊者選角 54×54、玩家列表 24×24、對局 50×50、缺圖／尺寸／alpha／邊界錯誤快取與幾何 fallback 均通過，破陣者與其他角色／怪物回歸未受影響。
- 2026-08-29｜T029 headless 效能：`.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_performance -v`，模擬 10.00 秒（600 幀），預載入來源讀檔 144 次；量測平均 `7019.63 FPS`、最大單幀間隔 `0.23 ms`、量測期間 `pygame.image.load` 為 `0` 次，三項門檻通過。
- 2026-08-29｜T028 headless UI smoke／人工視覺驗收：以 dummy SDL 正式呼叫 `draw_selection()`、`draw_match()` 與成功攻擊動作輸出選角、對局待機、對局攻擊快照並人工檢查；狙擊者卡片、50×50 對局角色、24×24 玩家列表圖示、文字與地圖層均完整，八方向／22.5 度分界、技能、死亡／重生、fallback 與其他角色回歸由同批 headless 測試覆蓋。OS-level Pygame 視窗未被桌面自動化工具列出，因此未執行實際滑鼠鍵盤操作，限制已保留在本紀錄。
- 2026-08-29｜T030 交付範圍檢查：`git status --short` 顯示的修改只有狙擊者功能所需程式、測試與 `specs/009-sniper-sprite-animation/`，狙擊者 PNG 計數為 72；既有未追蹤 `day3/` 與 `sample.png` 已確認保留且未納入本功能，暫存驗證腳本均不存在。
- 2026-08-29｜頭部校正後針對性回歸（前一版來源畫布）：執行 `.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q`，共 75 項通過；包含固定來源畫布分支、原有品質閘門、八方向與選角／對局／玩家列表 fallback。
- 2026-08-29｜T027 最終完整回歸：執行 `.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q`，共 266 項通過；`.\.venv\Scripts\python.exe -m compileall -q pvpve_escape` 與 `git diff --check` 均通過。
- 2026-08-29｜T029 前一版最終效能輸出：同一完整回歸中的 600 幀／10.00 秒模擬平均 `7491.33 FPS`、最大單幀間隔 `0.17 ms`、量測期間圖片讀取 `0` 次；門檻全部通過。
- 2026-08-29｜狙擊者頭部比例校正：使用者指出長槍外伸使各方向頭部顯示大小不一致；以每方向待機頭盔／面罩垂直錨點為基準，將同方向 idle、move、attack 的完整角色以最近鄰重新縮放並置中到固定 1024×1024 畫布。QA 結果 `checked=72 expected=72`、`failures=0`、`head_anchor_height_min=380.00 max=380.00`、`deterministic_matches=72/72`、`ASSET_QA=PASS`；人工拼圖確認頭部大小、長槍與手部連接、八方向背面語意均保留。

- 2026-08-29｜整體尺寸校正後針對性回歸（前一版）：狙擊者 `fit_mode` 改為與破陣者相同的 `visible_extent`，以完整 `alpha >= 64` 可見外框填滿 50×50／54×54／24×24，確保八個角度與破陣者使用一致的角色佔位規則；執行 `.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q`，共 75 項通過，並人工檢查八方向預覽。

- 2026-08-29｜整體尺寸校正後針對性回歸（前一版含縮放後置中）：狙擊者 `fit_mode` 改為與破陣者相同的 `visible_extent`，以完整 `alpha >= 64` 可見外框填滿 50×50／54×54／24×24，並在縮放後安全置中；執行 `.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q`，共 75 項通過，並人工檢查八方向預覽。

## 最新角色本體尺寸穩定化驗證

- 2026-08-29｜角色本體基準資產 QA：以每方向 idle／move／attack 共 9 幀的 `alpha >= 64` 身體核心聯合外框重新縮放狙擊者 72 張完整圖片；共同身體核心高度目標為 812 個來源像素，輸出 QA 量測為 812～828（最近鄰與低解析度量測誤差在 16 個來源像素內），武器外伸不參與比例。結果 `checked=72 expected=72`、`body_core_union_heights` 全方向通過、`deterministic_matches=72/72`、`BODY_ASSET_QA=PASS`。載入器使用 `source_canvas`，同方向動畫幀共用比例，人工預覽確認走路與朝上角色本體大小穩定。
- 2026-08-29｜方向聯合外框後針對性回歸（前一版）：執行 `\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q`，共 75 項通過；覆蓋八方向 idle／move／attack 的固定來源畫布、品質閘門與渲染 fallback。
- 2026-08-29｜方向聯合外框後最終完整回歸（前一版）：執行 `\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q`，共 266 項通過；地圖量測平均 `93.43 FPS`，精靈模擬量測平均 `6653.60 FPS`、最大單幀間隔 `0.22 ms`、量測期間圖片讀取 `0` 次。
- 2026-08-29｜角色本體基準後針對性回歸：執行 `\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_sprite_animation pvpve_escape.tests.test_rendering -q`，共 75 項通過；覆蓋固定來源畫布、身體本體比例、八方向 idle／move／attack、品質閘門與渲染 fallback。
- 2026-08-29｜角色本體基準後最終完整回歸：執行 `\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q`，共 266 項通過；地圖量測平均 `95.30 FPS`，精靈模擬量測平均 `6521.24 FPS`、最大單幀間隔 `0.23 ms`、量測期間圖片讀取 `0` 次。

- 2026-08-29｜本地 code review：發現角色規格雖已保存 `preload_display_sizes`，主迴圈與通用預載入入口仍重複寫死 `(50, 54, 24)`，可能在尺寸設定變更後漏暖身正確顯示尺寸；已改為省略參數時讀取各角色規格，並新增回歸測試確認規格值會被採用。這是唯一需要直接修正的問題，未發現角色動畫、遊戲規則、fallback 或效能的其他必要修正。
- 2026-08-29｜code review 修正後回歸：`.\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_main pvpve_escape.tests.test_sprite_animation -q` 共 32 項通過；完整 `unittest discover` 共 267 項通過，地圖平均 `95.75 FPS`、精靈模擬平均 `6532.95 FPS`、最大單幀間隔 `0.23 ms`、量測期間圖片讀取 `0` 次；`compileall` 與 `git diff --check` 亦通過。
- 2026-08-29｜人工驗收：使用者已完成選角、對局、八方向、移動／攻擊動畫、技能、死亡／重生、玩家列表與其他角色／怪物情境測試，確認沒有問題。
- 2026-08-29｜發布前文件檢查：重新檢查 `spec.md`、`plan.md`、`tasks.md`、`research.md`、`data-model.md`、`quickstart.md`、`checklists/requirements.md`、憲章與角色製作技能；SDD 跨文件分析確認需求覆蓋、任務依賴、API、角色本體比例規則與驗證紀錄一致，未發現待修正問題。`T031` 保留未完成，等待 PR 合併與發布後補記實際連結及提交資訊。

## 手動端到端驗證

啟動遊戲：

```powershell
.\.venv\Scripts\python.exe -m pvpve_escape
```

依序執行：

1. 在選角畫面選擇狙擊者，確認卡片顯示偵察狙擊兵待機外觀且文字沒有被遮住。
2. 進入對局，將瞄準方向切換到右、右下、下、左下、左、左上、上、右上；確認上、左上、右上為背面，並在各個 22.5 度分界角測試面向歸屬穩定。
3. 在每個方向停止移動，確認待機圖片的角色、長槍與瞄具完整；再使用 WASD，確認四格移動動畫循環且不漂移或裁切。
4. 按住左鍵蓄力但未放開，並分別模擬無彈藥、冷卻中或其他條件不足，確認不誤播攻擊動畫；成功放開後確認四格攻擊動畫播放。
5. 分別使用 Space 戰術配件與右鍵終極技能，確認兩者使用同一套攻擊動畫。
6. 移動中施放成功動作，確認攻擊動畫優先；動畫完成後回到當下移動或待機狀態。
7. 觀察玩家列表，確認狙擊者圖示與名稱、狀態文字完整可見；存活角色沒有常駐底圈，死亡／護盾／控場標記仍可辨識。
8. 測試死亡與重生，確認死亡標記保留，重生後沒有上一條命的攻擊幀殘留。
9. 在測試環境使任一狙擊者圖片缺失或不可用，重新繪製選角與對局，確認角色改用幾何外觀且遊戲不中斷。
10. 選擇其他角色並觀察怪物，確認其外觀、技能、碰撞與行為未改變。
11. 執行 T029 的 headless 效能量測並連續遊玩 10 秒，確認平均每秒至少 60 次畫面更新、最大單幀間隔不超過 100 毫秒、量測期間沒有圖片讀取，且沒有閃爍、空白角色、方向錯置或裁切。

## 通過條件

- 狙擊者資產檢查 72/72 通過。
- 已記錄的基線測試與新增針對性測試、完整 `unittest`、狙擊者 headless 效能測試、`compileall` 與 `git diff --check` 通過。
- 八方向、待機、移動、蓄力射擊、戰術配件、終極技能、攻擊優先、死亡／重生與 fallback 手動情境通過。
- 選角、對局與玩家列表顯示一致，且其他角色與怪物回歸驗收通過。
