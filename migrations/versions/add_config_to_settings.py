"""Add config field to Settings

Revision ID: add_config_field
Revises: 3b98ff5050a8
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import json

# revision identifiers, used by Alembic.
revision = 'add_config_field'
down_revision = '3b98ff5050a8'
branch_labels = None
depends_on = None

def upgrade():
    # Default config value
    default_config = json.dumps({
        'blur_faces': True,
        'confidence_threshold': 0.2,
        'camera_index': 0,
        'camera_name': 'Camera 1',
        'email_notifications': False,
        'sms_notifications': False
    })
    
    # Add config column with default value
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('config', sa.JSON(), nullable=False, server_default=default_config))

def downgrade():
    # Remove config column
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_column('config')

