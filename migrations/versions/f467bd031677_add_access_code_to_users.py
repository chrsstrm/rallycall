"""add access_code to users

Revision ID: f467bd031677
Revises: a0da8efecb82
Create Date: 2020-12-31 02:41:06.022898

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f467bd031677'
down_revision = 'a0da8efecb82'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('access_code', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'access_code')
    # ### end Alembic commands ###