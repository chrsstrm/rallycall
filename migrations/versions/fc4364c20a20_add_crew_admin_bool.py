"""add crew admin bool

Revision ID: fc4364c20a20
Revises: f467bd031677
Create Date: 2021-01-09 03:54:52.522409

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc4364c20a20'
down_revision = 'f467bd031677'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('crew_admin', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'crew_admin')
    # ### end Alembic commands ###
