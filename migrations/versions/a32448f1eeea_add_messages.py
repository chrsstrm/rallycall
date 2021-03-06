"""add messages

Revision ID: a32448f1eeea
Revises: cb4f6d1bd164
Create Date: 2020-12-27 23:55:01.144265

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a32448f1eeea'
down_revision = 'cb4f6d1bd164'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('messages',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('listen_count', sa.Integer(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('status', sa.Enum('created', 'listened_to', 'deleted', name='message_status'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('messages')
    # ### end Alembic commands ###
