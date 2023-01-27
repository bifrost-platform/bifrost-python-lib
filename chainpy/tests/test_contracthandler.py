from chainpy.eventbridge.multichainmonitor import MultiChainMonitor


def test_collect_events():
    # check if Unify_Split of multiple contracts are correctly collected.
    multi_chain_monitor = MultiChainMonitor.from_config_files("chainpy/tests/data/entity.main.template.json",
                                                              "chainpy/tests/data/private.json")

    for chain in multi_chain_monitor.supported_chain_list:
        chain_manager = multi_chain_monitor.get_chain_manager_of(chain)
        detected_events = chain_manager.small_ranged_collect_events("Unify_Split", 383000, 384000)
        detected_events += chain_manager.small_ranged_collect_events("Vault", 383000, 384000)
        detected_events += chain_manager.small_ranged_collect_events("Socket", 383000, 384000)

        for detected_event in detected_events:
            event_name = detected_event.event_name

            multi_chain_monitor.monitor_logger.formatted_log(
                log_id=f"{event_name}:{detected_event.transaction_hash}",
                related_chain=detected_event.chain_index.name,
                log_data="Detected"
            )
