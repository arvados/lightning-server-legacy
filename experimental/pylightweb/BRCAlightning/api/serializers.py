from django.forms import widgets
from rest_framework import serializers
from tile_library.models import TileLocusAnnotation, GenomeStatistic, TileVariant

class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = TileVariant
        fields = ('tile_variant_name', 'num_positions_spanned', 'conversion_to_cgf', 'length', 'sequence', 'start_tag', 'end_tag')

class LocusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TileLocusAnnotation
        fields = ('assembly', 'chromosome', 'begin_int', 'end_int')

class GenomeVariantInTileVariantSerializer(serializers.Serializer):
    tile_variant_hex_string = serializers.CharField(max_length=15)
    start_locus_relative_to_tile = serializers.IntegerField()
    end_locus_relative_to_tile = serializers.IntegerField()
    start_locus_relative_to_ref = serializers.IntegerField()
    end_locus_relative_to_ref = serializers.IntegerField()
    reference_bases = serializers.CharField()
    alternate_bases = serializers.CharField()


class PopulationVariantSerializer(serializers.Serializer):
    human_name = serializers.CharField(max_length=200)
    phase_A_sequence = serializers.CharField(style={'type': 'textarea'})
    phase_B_sequence = serializers.CharField(style={'type': 'textarea'})
    phase_groups_known = serializers.BooleanField(default=False)

class PopulationQuerySerializer(serializers.Serializer):
    INDEX_CHOICES = (
        (0, '0-indexed'),
        (1, '1-indexed'),
        )
    assembly = serializers.ChoiceField(choices=TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chromosome = serializers.ChoiceField(choices=TileLocusAnnotation.CHR_CHOICES)
    indexing = serializers.ChoiceField(choices=INDEX_CHOICES, default=0)
    target_base = serializers.IntegerField()
    number_around = serializers.IntegerField(default=0)

class PopulationRangeQuerySerializer(serializers.Serializer):
    INDEX_CHOICES = (
        (0, '0-indexed'),
        (1, '1-indexed'),
        )
    assembly = serializers.ChoiceField(choices=TileLocusAnnotation.SUPPORTED_ASSEMBLY_CHOICES)
    chromosome = serializers.ChoiceField(choices=TileLocusAnnotation.CHR_CHOICES)
    indexing = serializers.ChoiceField(choices=INDEX_CHOICES, default=0)
    lower_base = serializers.IntegerField()
    upper_base = serializers.IntegerField()
