from rest_framework import serializers
from .models import ConversionRequest, ConversionHistory


class ConversionRequestSerializer(serializers.ModelSerializer):
    input_size_mb = serializers.SerializerMethodField()
    output_size_mb = serializers.SerializerMethodField()
    compression_percentage = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = ConversionRequest
        fields = (
            'id', 'user_email', 'input_filename', 'input_format', 'input_size',
            'input_size_mb', 'output_format', 'output_quality', 'custom_settings',
            'output_filename', 'output_size', 'output_size_mb', 'status', 'progress',
            'error_message', 'created_at', 'started_at', 'completed_at', 'expires_at',
            'duration', 'duration_formatted', 'conversion_time', 'compression_ratio',
            'compression_percentage'
        )
        read_only_fields = (
            'id', 'input_filename', 'input_format', 'input_size', 'output_filename',
            'output_size', 'status', 'progress', 'error_message', 'created_at',
            'started_at', 'completed_at', 'expires_at', 'duration', 'conversion_time',
            'compression_ratio'
        )

    def get_input_size_mb(self, obj):
        return obj.get_input_size_mb()

    def get_output_size_mb(self, obj):
        return obj.get_output_size_mb()

    def get_compression_percentage(self, obj):
        return obj.get_compression_percentage()

    def get_duration_formatted(self, obj):
        return obj.get_duration_formatted()

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'


class ConversionCreateSerializer(serializers.ModelSerializer):
    input_file = serializers.FileField()

    class Meta:
        model = ConversionRequest
        fields = ('input_file', 'output_format', 'output_quality', 'custom_settings')

    def validate_input_file(self, value):
        """Validate the input file"""
        # Check file size (max 500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 500MB")

        # Check file extension
        allowed_extensions = [
            'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v',
            'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'
        ]
        
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '{file_extension}' not supported. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )

        return value

    def validate(self, attrs):
        """Validate conversion settings"""
        input_file = attrs.get('input_file')
        output_format = attrs.get('output_format')
        
        if input_file and output_format:
            input_extension = input_file.name.split('.')[-1].lower()
            
            # Don't allow converting to the same format
            if input_extension == output_format:
                raise serializers.ValidationError(
                    "Output format cannot be the same as input format"
                )

        return attrs


class ConversionHistorySerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    input_size_mb = serializers.SerializerMethodField()
    output_size_mb = serializers.SerializerMethodField()
    conversion_type = serializers.SerializerMethodField()

    class Meta:
        model = ConversionHistory
        fields = (
            'id', 'user_email', 'conversion_type', 'input_format', 'output_format',
            'input_size', 'input_size_mb', 'output_size', 'output_size_mb',
            'conversion_time', 'success', 'timestamp'
        )

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'

    def get_input_size_mb(self, obj):
        return round(obj.input_size / (1024 * 1024), 2)

    def get_output_size_mb(self, obj):
        if obj.output_size:
            return round(obj.output_size / (1024 * 1024), 2)
        return 0

    def get_conversion_type(self, obj):
        return f"{obj.input_format} → {obj.output_format}"
