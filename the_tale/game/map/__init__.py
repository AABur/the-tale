from django_next.utils.app_settings import app_settings

settings = app_settings('MAP', 
                        CELL_SIZE=20,
                        CELL_LENGTH=1.0,
                        
                        # map generation settings
                        GEN_CONFIG_FILE='./game/map/management/commands/map_generator/config.py',
                        GEN_REGION_OUTPUT='./static/game/map/data/region.js'
                        )
