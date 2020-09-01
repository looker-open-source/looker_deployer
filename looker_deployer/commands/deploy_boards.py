import logging
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client

logger = deploy_logging.get_logger(__name__)


class MultipleAssetsFoundError(Exception):
    """Exception raised if multiple assets are found"""

    def __init__(self, asset_name, message="Found multiple entries for asset. Please remove duplicates"):
        self.asset_name = asset_name
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.asset_name} -> {self.message}"


class TargetContentNotFound(Exception):
    """Exception raised if content is not found in target instance"""

    def __init__(self, missing_dashes, missing_looks, message="Content not found in target instance."):
        self.missing_dashes = missing_dashes
        self.missing_looks = missing_looks
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} -> dashes: {self.missing_dashes}, looks: {self.missing_looks}"


def match_dashboard_id(source_dashboard_id, source_sdk, target_sdk):
    source = source_sdk.dashboard(str(source_dashboard_id))
    logger.debug("Attempting dashboard match", extra={"title": source.title, "slug": source.slug, "id": source.id})
    target_dash = target_sdk.search_dashboards(slug=source.slug)

    if len(target_dash) > 1:
        raise MultipleAssetsFoundError(source.title)

    assert len(target_dash) == 1, f"Could not find dashboard {source.title} in target env. Has it been deployed?"

    target_id = target_dash[0].id
    logger.debug("Found dashboard", extra={"id": target_id})

    return target_id


def match_look_id(source_look_id, source_sdk, target_sdk):
    source = source_sdk.look(source_look_id)
    logger.debug("Attempting look match", extra={"title": source.title, "id": source.id})
    target_look = target_sdk.search_looks(title=source.title)

    if len(target_look) > 1:
        raise MultipleAssetsFoundError(source.title)

    assert len(target_look) == 1, f"Could not find look {source.title} in target env. Has it been deployed?"

    target_id = target_look[0].id
    logger.debug("Found look", extra={"id": target_id})

    return target_id


def return_board(board_name, source_sdk):
    logger.debug("Searching boards", extra={"title": board_name})
    board_list = source_sdk.search_homepages(title=board_name)

    if len(board_list) > 1:
        raise MultipleAssetsFoundError(board_name)

    assert len(board_list) == 1, "Could not find board! Double check available titles and try again."

    logger.debug("Found board", extra={"board": board_list})
    return board_list[0]


def create_or_update_board(source_board_object, target_sdk, title_override=None):

    # Determine if board already exists in target environment
    search_title = title_override or source_board_object.title
    search_res = target_sdk.search_homepages(title=search_title)
    assert len(search_res) < 2, "More than one board found! Refine your search or remove duplicate names."

    try:
        assert len(search_res) == 1

    # If board does not exist then create
    except AssertionError:
        logger.info(
            "No pre-existing board found. Creating new board in target environment",
            extra={"title": search_title}
        )

        new_board = models.WriteHomepage(
            title=source_board_object.title,
            description=source_board_object.description
        )

        resp = target_sdk.create_homepage(new_board)
        logger.info("Board created", extra={"id": resp.id})
        return resp.id

    # If board already exists, clear out sections and update
    logger.info(
        "Found board in target instance. Updating and rebuilding content",
        extra={"title": search_title}
    )

    target_board = search_res[0]

    # Clear out existing sections
    section_list = [i.id for i in target_board.homepage_sections]
    logger.debug("Found sections to clear", extra={"section_list": section_list})

    for section in section_list:
        logger.debug("Clearing section for refresh", extra={"section_id": section})
        target_sdk.delete_homepage_section(section)

    # Update
    update_board = models.WriteHomepage(
        title=source_board_object.title,
        description=source_board_object.description
    )

    resp = target_sdk.update_homepage(target_board.id, update_board)
    logger.info("Board updated", extra={"id": resp.id})
    return resp.id


def create_board_section(source_board_section_object, target_board_id, target_sdk):
    new_board_section = models.WriteHomepageSection(
        title=source_board_section_object.title,
        description=source_board_section_object.description,
        homepage_id=target_board_id
    )

    logger.info("Creating Section", extra={"board_id": target_board_id, "section_title": new_board_section.title})
    resp = target_sdk.create_homepage_section(new_board_section)
    logger.info("Section created", extra={"section_id": resp.id})
    return resp.id


def create_board_item(source_board_item_object, target_board_section_id, source_sdk, target_sdk):

    dashboard_id = None
    look_id = None

    if source_board_item_object.dashboard_id:
        dashboard_id = match_dashboard_id(source_board_item_object.dashboard_id, source_sdk, target_sdk)
    if source_board_item_object.look_id:
        look_id = match_look_id(source_board_item_object.look_id, source_sdk, target_sdk)

    new_board_item = models.WriteHomepageItem()
    new_board_item.__dict__.update(source_board_item_object.__dict__)
    new_board_item.dashboard_id = dashboard_id
    new_board_item.look_id = look_id
    new_board_item.homepage_section_id = target_board_section_id

    logger.info(
        "Creating item",
        extra={
            "section_id": new_board_item.homepage_section_id,
            "dashboard_id": new_board_item.dashboard_id,
            "look_id": new_board_item.look_id,
            "url": new_board_item.url
        }
    )
    resp = target_sdk.create_homepage_item(new_board_item)
    logger.info("Item created", extra={"id": resp.id})

    return resp


def audit_board_content(board_object, source_sdk, target_sdk):
    dash_list = []
    look_list = []

    missing_dashes = []
    missing_looks = []

    for i in board_object.homepage_sections:
        for j in i.homepage_items:
            if j.dashboard_id:
                dash_list.append(j.dashboard_id)
            if j.look_id:
                look_list.append(j.look_id)

    for dash in dash_list:
        try:
            match_dashboard_id(dash, source_sdk, target_sdk)
        except AssertionError:
            dash_title = source_sdk.dashboard(str(dash)).title
            missing_dashes.append({"dash_id": dash, "dash_title": dash_title})

    for look in look_list:
        try:
            match_look_id(look, source_sdk, target_sdk)
        except AssertionError:
            look_title = source_sdk.look(look).title
            missing_looks.append({"look_id": look, "look_title": look_title})

    return (missing_dashes, missing_looks)


def send_boards(board_name, source_sdk, target_sdk, title_override=None, allow_partial=False):
    source_board = return_board(board_name, source_sdk)

    missing_dashes, missing_looks = audit_board_content(source_board, source_sdk, target_sdk)
    if not allow_partial and (missing_dashes or missing_looks):
        logger.error(
            "Missing Content. Make sure it's deployed or rerun with allow-partial flag.",
            extra={"missing_dashboards": missing_dashes, "missing_looks": missing_looks}
        )
        raise TargetContentNotFound(missing_dashes, missing_looks)
    elif missing_dashes or missing_looks:
        logger.warning(
            "Missing content warning.",
            extra={"missing_dashboards": missing_dashes, "missing_looks": missing_looks}
        )
    else:
        logger.info("All content accounted for!")

    target_board_id = create_or_update_board(source_board, target_sdk, title_override)

    for section in source_board.homepage_sections:
        target_section_id = create_board_section(section, target_board_id, target_sdk)

        for item in section.homepage_items:
            try:
                create_board_item(item, target_section_id, source_sdk, target_sdk)
            except AssertionError:
                if allow_partial:
                    logger.warning("Could not find content!", extra={"item": item.title})
                    pass
                else:
                    raise


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)

        send_boards(args.board, source_sdk, target_sdk, args.title_change, args.allow_partial)
