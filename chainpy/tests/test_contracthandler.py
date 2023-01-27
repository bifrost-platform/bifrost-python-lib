from chainpy.eventbridge.multichainmonitor import MultiChainMonitor


def test_collect_events():
    # check if Unify_Split of multiple contracts are correctly collected.
    multi_chain_monitor = MultiChainMonitor.from_config_files("chainpy/tests/data/entity.main.template.json",
                                                              "chainpy/tests/data/private.json")

    for chain in multi_chain_monitor.supported_chain_list:
        chain_manager = multi_chain_monitor.get_chain_manager_of(chain)
        detected_events = chain_manager.small_ranged_collect_events("Unify_Split", 383000, 384000)

        for detected_event in detected_events:
            event_name = detected_event.event_name
            event_type = multi_chain_monitor.__events_types[event_name]

            chain_event = event_type(detected_event, multi_chain_monitor)

            multi_chain_monitor.monitor_logger.formatted_log(
                log_id=chain_event.summary(),
                related_chain=chain_event.on_chain,
                log_data="Detected"
            )
